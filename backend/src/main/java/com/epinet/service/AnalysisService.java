package com.epinet.service;

import com.epinet.model.AnalysisRun;
import com.epinet.repository.AnalysisRunRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.MediaType;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.LocalDateTime;

/**
 * Async service that calls the Python ML microservice and persists results.
 * All DB writes are transactional; the async method runs in Spring's task executor.
 */
@Service
public class AnalysisService {

    private static final Logger log = LoggerFactory.getLogger(AnalysisService.class);

    private final AnalysisRunRepository repo;
    private final WebClient webClient;
    private final ObjectMapper mapper = new ObjectMapper();

    public AnalysisService(
            AnalysisRunRepository repo,
            @Value("${ml.service.url:http://localhost:8000}") String mlUrl
    ) {
        this.repo = repo;
        this.webClient = WebClient.builder()
                .baseUrl(mlUrl)
                .codecs(config -> config.defaultCodecs().maxInMemorySize(10 * 1024 * 1024))
                .build();
    }

    /**
     * Runs asynchronously after the upload controller responds 202.
     * Transitions status: PROCESSING → COMPLETED | FAILED.
     */
    @Async
    @Transactional
    public void runAnalysis(String analysisId, byte[] fileBytes, String filename) {
        log.info("Starting async analysis for id={}", analysisId);

        // Mark as PROCESSING
        AnalysisRun run = repo.findById(analysisId)
                .orElseThrow(() -> new IllegalStateException("Run not found: " + analysisId));
        run.setStatus(AnalysisRun.Status.PROCESSING);
        repo.save(run);

        try {
            // Call ML microservice
            MultipartBodyBuilder bodyBuilder = new MultipartBodyBuilder();
            bodyBuilder.part("file", new ByteArrayResource(fileBytes) {
                @Override public String getFilename() { return filename; }
            }).contentType(MediaType.TEXT_PLAIN);

            String resultJson = webClient.post()
                    .uri("/analyze")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(BodyInserters.fromMultipartData(bodyBuilder.build()))
                    .retrieve()
                    .bodyToMono(String.class)
                    .block();

            // Validate that it is parseable JSON
            mapper.readTree(resultJson);

            run.setResultJson(resultJson);
            run.setStatus(AnalysisRun.Status.COMPLETED);
            run.setCompletedAt(LocalDateTime.now());
            log.info("Analysis {} COMPLETED", analysisId);

        } catch (Exception ex) {
            log.error("Analysis {} FAILED: {}", analysisId, ex.getMessage(), ex);
            run.setStatus(AnalysisRun.Status.FAILED);
            run.setErrorMessage(ex.getMessage());
            run.setCompletedAt(LocalDateTime.now());
        }

        repo.save(run);
    }
}
