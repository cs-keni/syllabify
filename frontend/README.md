# Frontend

Frontend React application for Syllabify.

## Tech Stack

- **Framework**: React
- **Styling**: Tailwind CSS
- **Linting**: ESLint
- **Formatting**: Prettier

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── api/                    # API client calls
│   ├── components/             # Reusable UI components
│   ├── pages/                  # Page-level components
│   ├── hooks/                  # Custom React hooks
│   ├── styles/                 # Stylesheets
│   ├── App.jsx                 # Main App component
│   └── main.jsx                # React entry point
├── package.json
├── .eslintrc.cjs
├── .prettierrc
└── README.md
```

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run development server:
   ```bash
   npm run dev
   ```

3. Build for production:
   ```bash
   npm run build
   ```

## Code Quality

```bash
# Check formatting
npm run format:check

# Auto-format code
npm run format

# Check linting
npm run lint

# Fix linting issues
npm run lint:fix
```
