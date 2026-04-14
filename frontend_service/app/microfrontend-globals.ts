import * as React from 'react';
import * as ReactDOM from 'react-dom/client';
import * as MaterialUI from '@mui/material';
import * as Recharts from 'recharts';

// Expose to window for microfrontends
declare global {
  interface Window {
    React: typeof React;
    ReactDOM: typeof ReactDOM;
    MaterialUI: typeof MaterialUI;
    Recharts: typeof Recharts;
    RelibankMicrofrontends?: any;
  }
}

// Only execute on client-side (not during SSR)
if (typeof window !== 'undefined') {
  window.React = React;
  window.ReactDOM = ReactDOM;
  window.MaterialUI = MaterialUI;
  window.Recharts = Recharts;

  console.log('[Microfrontend Globals] React, ReactDOM, MaterialUI, and Recharts exposed to window');
}
