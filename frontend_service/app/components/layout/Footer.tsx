import { useState, useEffect } from 'react';
import { Box, Typography, Collapse, IconButton } from '@mui/material';
import { ExpandMore as ExpandMoreIcon, ExpandLess as ExpandLessIcon } from '@mui/icons-material';

export const Footer = () => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    // Access New Relic Browser session ID from sessionStorage
    // Retry a few times because New Relic might not have initialized yet
    let attempts = 0;
    const maxAttempts = 10;

    const checkForSessionId = () => {
      if (typeof window === 'undefined') return;

      attempts++;

      try {
        // Check all possible storage locations
        const nrbaSession = sessionStorage.getItem('NRBA_SESSION');
        const nrbaSessionLocal = localStorage.getItem('NRBA_SESSION');

        if (nrbaSession) {
          setSessionId(nrbaSession);
          console.log('[Footer] New Relic Browser session ID loaded:', nrbaSession);
          return true;
        }

        if (nrbaSessionLocal) {
          setSessionId(nrbaSessionLocal);
          console.log('[Footer] New Relic Browser session ID loaded:', nrbaSessionLocal);
          return true;
        }

        // Fallback: Check newrelic object
        if ((window as any).newrelic) {
          const nr = (window as any).newrelic;
          const id = nr.info?.session ||
                     nr.info?.sessionId ||
                     nr.info?.sessionTraceId ||
                     nr.session?.id ||
                     nr.getContext?.()?.traceId;

          if (id) {
            setSessionId(id);
            console.log('[Footer] New Relic Browser session ID loaded:', id);
            return true;
          }
        }

        return false;
      } catch (error) {
        console.error('[Footer] Error accessing New Relic session ID:', error);
        return false;
      }
    };

    // Try immediately
    if (checkForSessionId()) return;

    // Retry with delays if not found
    const interval = setInterval(() => {
      if (checkForSessionId() || attempts >= maxAttempts) {
        clearInterval(interval);
        if (attempts >= maxAttempts) {
          console.warn('[Footer] Failed to get New Relic session ID after', maxAttempts, 'attempts');
        }
      }
    }, 500); // Check every 500ms

    return () => clearInterval(interval);
  }, []);

  return (
    <Box component="footer" sx={{
      py: 2,
      px: 2,
      backgroundColor: 'white',
      borderTop: '1px solid #e5e7eb',
      textAlign: 'center',
      borderRadius: '0 0 12px 12px',
      color: 'text.secondary'
    }}>
      {/* Main footer text */}
      <Typography variant="body2" sx={{ mb: 0.5, lineHeight: 1.6 }}>
        Is this bank real? Is your money? Are you? We're only certain about the first one. Please recognize this is a demo.
      </Typography>

      {/* Copyright and expand button */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1, mb: 1 }}>
        <Typography variant="body2">
          © 2023 ReliBank. All rights reserved.
        </Typography>

        <IconButton
          id="footer-toggle-debug-btn"
          size="small"
          onClick={() => setExpanded(!expanded)}
          sx={{ ml: 0.5 }}
          aria-label="Show debug info"
        >
          {expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
        </IconButton>
      </Box>

      {/* Collapsible debug section */}
      <Collapse in={expanded}>
        {sessionId && (
          <Box sx={{ mt: 1, pt: 1.5, borderTop: '1px solid #e5e7eb' }}>
            <Box sx={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 1,
              bgcolor: 'rgba(0, 0, 0, 0.03)',
              py: 0.5,
              px: 1.25,
              borderRadius: '6px',
              border: '1px solid rgba(0, 0, 0, 0.06)'
            }}>
              <Typography
                variant="caption"
                sx={{
                  fontFamily: 'monospace',
                  fontSize: '0.7rem',
                  color: 'text.secondary',
                  fontWeight: 500
                }}
              >
                NR Session:
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  fontFamily: 'monospace',
                  fontSize: '0.7rem',
                  color: 'primary.main',
                  fontWeight: 600
                }}
              >
                {sessionId}
              </Typography>
            </Box>
          </Box>
        )}
      </Collapse>
    </Box>
  );
};
