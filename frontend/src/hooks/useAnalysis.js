import { useCallback, useRef, useState } from 'react';
import { uploadCsv, getStatus, getResult } from '../api';

const POLL_INTERVAL_MS = 2000;

/**
 * Custom hook managing the full upload → poll → result lifecycle.
 * Returns state and the `startUpload` action.
 */
export function useAnalysis() {
  const [phase, setPhase] = useState('idle'); // idle | uploading | processing | done | error
  const [analysisId, setAnalysisId] = useState(null);
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [filename, setFilename] = useState('');
  const pollRef = useRef(null);

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  };

  const startUpload = useCallback(async (file) => {
    stopPolling();
    setPhase('uploading');
    setResult(null);
    setErrorMsg('');
    setFilename(file.name);

    try {
      const { analysisId: id } = await uploadCsv(file);
      setAnalysisId(id);
      setPhase('processing');

      // Poll every 2 s until COMPLETED or FAILED
      pollRef.current = setInterval(async () => {
        try {
          const status = await getStatus(id);
          if (status.status === 'COMPLETED') {
            stopPolling();
            const data = await getResult(id);
            setResult(data);
            setPhase('done');
          } else if (status.status === 'FAILED') {
            stopPolling();
            setErrorMsg(status.errorMessage || 'Analysis failed on the server.');
            setPhase('error');
          }
        } catch (err) {
          stopPolling();
          setErrorMsg(err.message);
          setPhase('error');
        }
      }, POLL_INTERVAL_MS);

    } catch (err) {
      setErrorMsg(err.message);
      setPhase('error');
    }
  }, []);

  const reset = useCallback(() => {
    stopPolling();
    setPhase('idle');
    setAnalysisId(null);
    setResult(null);
    setErrorMsg('');
    setFilename('');
  }, []);

  return { phase, analysisId, result, errorMsg, filename, startUpload, reset };
}
