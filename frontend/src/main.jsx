/**
 * React entry point. Renders App into DOM.
 * TODO: Wrap with Router, auth provider. Add routes for Dashboard, Upload, Login.
 * DISCLAIMER: Project structure may change.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/index.css';

// StrictMode disabled: FullCalendar's toolbar duplicates when StrictMode double-mounts in dev.
// See https://github.com/fullcalendar/fullcalendar/issues/7254
ReactDOM.createRoot(document.getElementById('root')).render(<App />);
