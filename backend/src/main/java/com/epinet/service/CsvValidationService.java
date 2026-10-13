package com.epinet.service;

import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.Arrays;
import java.util.List;

/**
 * Validates the uploaded CSV before it reaches the ML service.
 * Checks: extension, size, header presence, required columns.
 */
public class CsvValidationService {

    private static final long MAX_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB

    private static final List<String> REQUIRED_GENE_COLUMNS = Arrays.asList(
            "CYP2D6", "CYP2C19", "CYP3A4", "CYP2C9",
            "VKORC1", "SLCO1B1", "TPMT", "DPYD", "UGT1A1", "ABCB1"
    );

    private CsvValidationService() {}

    /**
     * Validates the multipart file and returns its bytes.
     *
     * @throws ValidationException on any violation (message is forwarded to the client).
     */
    public static byte[] validate(MultipartFile file) throws IOException {
        String name = file.getOriginalFilename() == null ? "" : file.getOriginalFilename();

        if (!name.toLowerCase().endsWith(".csv")) {
            throw new ValidationException("Only .csv files are accepted. Received: " + name);
        }

        if (file.getSize() > MAX_SIZE_BYTES) {
            throw new ValidationException(
                    "File size " + file.getSize() / 1024 + " KB exceeds the 5 MB limit.");
        }

        byte[] bytes = file.getBytes();
        if (bytes.length == 0) {
            throw new ValidationException("Uploaded file is empty.");
        }

        // Parse the header row
        String content = new String(bytes).replace("\r\n", "\n").replace("\r", "\n");
        String[] lines = content.split("\n", 2);
        if (lines.length == 0 || lines[0].isBlank()) {
            throw new ValidationException("CSV is missing a header row.");
        }

        List<String> headers = Arrays.stream(lines[0].split(","))
                .map(String::trim)
                .toList();

        if (!headers.contains("sample_id")) {
            throw new ValidationException("CSV must have a 'sample_id' column.");
        }
        if (!headers.contains("phenotype")) {
            throw new ValidationException("CSV must have a 'phenotype' column.");
        }

        List<String> missingGenes = REQUIRED_GENE_COLUMNS.stream()
                .filter(g -> !headers.contains(g))
                .toList();
        if (!missingGenes.isEmpty()) {
            throw new ValidationException("CSV is missing gene columns: " + missingGenes);
        }

        return bytes;
    }

    /** Checked exception used only within the validation layer. */
    public static class ValidationException extends RuntimeException {
        public ValidationException(String message) { super(message); }
    }
}
