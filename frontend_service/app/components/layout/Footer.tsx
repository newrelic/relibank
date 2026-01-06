import { Box, Typography } from '@mui/material';

export const Footer = () => (
  <Box component="footer" sx={{
    py: 3,
    px: 2,
    backgroundColor: 'white',
    borderTop: '1px solid #e5e7eb',
    textAlign: 'center',
    borderRadius: '0 0 12px 12px',
    color: 'text.secondary'
  }}>
    <Typography variant="body2">
      Is this bank real? Is your money? Are you? We're only certain about the first one. Please recognize this is a demo.
    </Typography>
    <Typography variant="body2">
      © 2023 ReliBank. All rights reserved.
    </Typography>
  </Box>
);
