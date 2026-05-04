import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Home from '../pages/Homepage';

vi.mock('../assets/syllabify-logo-green.png', () => ({ default: 'logo.png' }));
vi.mock('../components/ThemeToggle', () => ({ default: () => null }));
vi.mock('../components/Footer', () => ({ default: () => null }));

function renderHome() {
  return render(
    <MemoryRouter>
      <Home />
    </MemoryRouter>
  );
}

describe('Homepage', () => {
  it('renders the main headline', () => {
    renderHome();
    expect(
      screen.getByText(/Turn syllabi into a balanced study plan/i)
    ).toBeInTheDocument();
  });

  it('renders Log in and Sign up CTAs', () => {
    renderHome();
    const loginLinks = screen.getAllByRole('link', { name: /log in/i });
    const signupLinks = screen.getAllByRole('link', { name: /sign up/i });
    expect(loginLinks.length).toBeGreaterThan(0);
    expect(signupLinks.length).toBeGreaterThan(0);
  });

  it('renders the three How It Works steps', () => {
    renderHome();
    expect(screen.getByText('Upload your syllabus')).toBeInTheDocument();
    expect(screen.getByText('Review & confirm')).toBeInTheDocument();
    expect(screen.getByText('Get a balanced schedule')).toBeInTheDocument();
  });
});
