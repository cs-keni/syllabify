import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SyllabusUpload from '../components/SyllabusUpload';

// Prevent real API calls
vi.mock('../api/client', () => ({
  parseSyllabus: vi.fn().mockResolvedValue({
    course_name: 'CS 422',
    assignments: [],
    meeting_times: [],
  }),
}));

const noop = () => {};

describe('SyllabusUpload', () => {
  it('renders Upload file and Paste text tabs', () => {
    render(<SyllabusUpload onComplete={noop} token="tok" />);
    expect(screen.getByText('Upload file')).toBeInTheDocument();
    expect(screen.getByText('Paste text')).toBeInTheDocument();
  });

  it('submit button is disabled when no file is selected', () => {
    render(<SyllabusUpload onComplete={noop} token="tok" />);
    const btn = screen.getByRole('button', { name: /parse syllabus/i });
    expect(btn).toBeDisabled();
  });

  it('shows Quick parse checkbox', () => {
    render(<SyllabusUpload onComplete={noop} token="tok" />);
    expect(screen.getByText(/Quick parse/i)).toBeInTheDocument();
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).not.toBeChecked();
  });

  it('submit button becomes enabled after pasting text', () => {
    render(<SyllabusUpload onComplete={noop} token="tok" />);
    fireEvent.click(screen.getByText('Paste text'));
    const textarea = screen.getByPlaceholderText(/Paste syllabus text here/i);
    fireEvent.change(textarea, { target: { value: 'Course: CS 422\nAssignment 1 due Jan 10' } });
    const btn = screen.getByRole('button', { name: /parse syllabus/i });
    expect(btn).not.toBeDisabled();
  });
});
