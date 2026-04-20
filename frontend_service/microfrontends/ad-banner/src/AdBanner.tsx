import type { AdBannerProps } from './types';

const AdBanner = ({ onSignUpClick }: AdBannerProps) => {
  const { Card, Box, Typography, Button, Collapse, Alert, CircularProgress } = window.MaterialUI;
  const { useState } = window.React;

  // State management
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Handle "More Info" toggle with telemetry
  const handleMoreInfoToggle = () => {
    const mfeAgent = window.RelibankMicrofrontends?.AdBanner?.agent;
    const startTime = performance.now();

    setIsExpanded(prev => !prev);

    if (mfeAgent) {
      const actionName = !isExpanded ? 'moreInfoExpanded' : 'moreInfoCollapsed';

      // Track page action
      if (mfeAgent.addPageAction) {
        mfeAgent.addPageAction(actionName, {
          location: 'dashboard',
          component: 'AdBanner'
        });
      }

      // Log the interaction
      if (mfeAgent.log) {
        mfeAgent.log(`More info section ${!isExpanded ? 'expanded' : 'collapsed'}`, {
          level: 'info'
        });
      }

      // Measure expansion timing (only when expanding)
      if (!isExpanded && mfeAgent.measure) {
        setTimeout(() => {
          const endTime = performance.now();
          mfeAgent.measure('moreInfoExpansion', {
            start: startTime,
            end: endTime
          });
        }, 300); // After animation completes
      }
    }

    console.log(`[AdBanner] More info section ${!isExpanded ? 'expanded' : 'collapsed'}`);
  };

  // Enhanced sign-up handler with API call and comprehensive telemetry
  const handleSignUpClick = async () => {
    const mfeAgent = window.RelibankMicrofrontends?.AdBanner?.agent;
    const startTime = performance.now();

    setIsLoading(true);
    setErrorMessage(null);

    // Track page action
    if (mfeAgent?.addPageAction) {
      mfeAgent.addPageAction('signUpAttempted', {
        productType: 'rewards-credit-card',
        source: 'dashboard-banner',
        location: 'dashboard'
      });
    }

    try {
      // Log the attempt
      if (mfeAgent?.log) {
        mfeAgent.log('Attempting rewards card application', {
          level: 'info'
        });
      }

      // Make API call to non-existent endpoint (will fail with 404)
      const response = await fetch('/bill-pay-service/rewards-card/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          productType: 'rewards-credit-card',
          source: 'dashboard-banner',
          timestamp: Date.now()
        })
      });

      if (!response.ok) {
        throw new Error(`API returned status ${response.status}`);
      }

      const data = await response.json();
      // Success handling (won't reach here with 404)
      console.log('[AdBanner] Application successful:', data);

    } catch (error: any) {
      const endTime = performance.now();

      // Notice error with rich context
      if (mfeAgent?.noticeError) {
        mfeAgent.noticeError(error, {
          component: 'AdBanner',
          action: 'signUp',
          endpoint: '/bill-pay-service/rewards-card/apply',
          statusCode: 404,
          productType: 'rewards-credit-card'
        });
      }

      // Log error
      if (mfeAgent?.log) {
        mfeAgent.log('Rewards card application failed', {
          level: 'error'
        });
      }

      // Record custom event
      if (mfeAgent?.recordCustomEvent) {
        mfeAgent.recordCustomEvent('RewardsCardApplicationFailed', {
          reason: 'endpoint_not_found',
          statusCode: 404,
          productType: 'rewards-credit-card',
          source: 'dashboard-banner'
        });
      }

      // Measure API call timing
      if (mfeAgent?.measure) {
        mfeAgent.measure('signUpApiCall', {
          start: startTime,
          end: endTime
        });
      }

      // Show error to user
      setErrorMessage('Unable to process application at this time. Please try again later or contact support.');
      console.error('[AdBanner] Sign up failed:', error);
    } finally {
      setIsLoading(false);
    }

    // Original callback
    if (onSignUpClick) {
      onSignUpClick();
    }
  };

  return (
    <Card sx={{
      p: 2,
      display: 'flex',
      flexDirection: 'column',
      gap: 2,
      background: 'linear-gradient(135deg, #1a3d1a 0%, #7a9b3e 100%)',
      color: 'white',
      borderRadius: '12px'
    }}>
      {/* Top Row: Icon + Title/Description + Sign Up Button */}
      <Box sx={{
        display: 'flex',
        flexDirection: { xs: 'column', sm: 'row' },
        alignItems: 'center',
        gap: 2
      }}>
        <Box sx={{
          fontSize: { xs: '2rem', sm: '2.5rem' },
          flexShrink: 0,
          filter: 'drop-shadow(0 2px 4px rgba(217, 119, 6, 0.3))'
        }}>
          🪙
        </Box>
        <Box sx={{ flexGrow: 1, textAlign: { xs: 'center', sm: 'left' } }}>
          <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 0.25, fontSize: { xs: '1rem', sm: '1.25rem' } }}>
            Get <Box component="span" sx={{ color: '#fbbf24' }}>5%</Box> Cash Back on Every Purchase!
          </Typography>
          <Typography variant="body2" sx={{ opacity: 0.95, fontSize: { xs: '0.875rem', sm: '1rem' } }}>
            Apply now for the ReliBank Rewards Credit Card and earn unlimited cash back with no annual fee.
          </Typography>
        </Box>
        <Button
          id="dashboard-rewards-signup-btn"
          variant="contained"
          size="medium"
          onClick={handleSignUpClick}
          disabled={isLoading}
          sx={{
            bgcolor: '#fbbf24',
            color: '#1a3d1a',
            fontWeight: 'bold',
            px: 3,
            '&:hover': {
              bgcolor: '#d97706'
            },
            '&:disabled': {
              bgcolor: '#fbbf24',
              opacity: 0.7,
              color: '#1a3d1a'
            },
            flexShrink: 0,
            width: { xs: '100%', sm: 'auto' }
          }}
        >
          {isLoading ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <CircularProgress size={20} sx={{ color: '#1a3d1a' }} />
              <span>Processing...</span>
            </Box>
          ) : (
            'Sign Up'
          )}
        </Button>
      </Box>

      {/* Error Alert */}
      {errorMessage && (
        <Alert
          severity="error"
          onClose={() => setErrorMessage(null)}
          sx={{
            bgcolor: 'rgba(211, 47, 47, 0.9)',
            color: 'white',
            '& .MuiAlert-icon': {
              color: 'white'
            }
          }}
        >
          {errorMessage}
        </Alert>
      )}

      {/* Terms and Conditions Expandable Section */}
      <Collapse in={isExpanded}>
        <Box sx={{
          bgcolor: 'rgba(0, 0, 0, 0.2)',
          borderRadius: '8px',
          p: 2
        }}>
          <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
            Terms and Conditions:
          </Typography>
          <Box component="ul" sx={{ margin: 0, paddingLeft: 2.5, fontSize: '0.875rem', lineHeight: 1.6 }}>
            <li>Cash back valid on all purchases except cryptocurrency, lottery tickets, and other cash back</li>
            <li>5% becomes 4.7% after our "processing fee" (we have to make money somehow)</li>
            <li>Annual fee: $0* (*$0 is technically a number)</li>
            <li>APR: Somewhere between "pretty good" and "yikes"</li>
            <li>Subject to credit approval, vibes check, and Mercury being in retrograde</li>
            <li>By clicking Sign Up, you agree you've read this (we know you didn't)</li>
            <li>Card design may vary. Probably will be boring.</li>
            <li>ReliBank is not responsible for impulse purchases made at 2 AM</li>
          </Box>
        </Box>
      </Collapse>

      {/* More Info Button - Bottom Position */}
      <Box sx={{ textAlign: { xs: 'center', sm: 'left' } }}>
        <Button
          onClick={handleMoreInfoToggle}
          sx={{
            color: 'white',
            textTransform: 'none',
            fontSize: '0.875rem',
            opacity: 0.9,
            '&:hover': {
              opacity: 1,
              bgcolor: 'rgba(255, 255, 255, 0.1)'
            },
            px: 1
          }}
        >
          {isExpanded ? 'Hide Details ▲' : 'More Info ▼'}
        </Button>
      </Box>
    </Card>
  );
};

export default AdBanner;
