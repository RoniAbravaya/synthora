/**
 * Utility Functions Tests
 * 
 * Tests for the utility functions in lib/utils.ts
 */

import { describe, it, expect } from 'vitest';
import { cn, formatDate, formatNumber, formatCompactNumber } from './utils';

describe('cn (classNames)', () => {
  it('merges class names correctly', () => {
    const result = cn('class1', 'class2');
    expect(result).toBe('class1 class2');
  });

  it('handles conditional classes', () => {
    const isActive = true;
    const result = cn('base', isActive && 'active');
    expect(result).toBe('base active');
  });

  it('handles falsy values', () => {
    const result = cn('base', false && 'hidden', null, undefined);
    expect(result).toBe('base');
  });

  it('merges Tailwind classes correctly', () => {
    // Tailwind merge should dedupe conflicting classes
    const result = cn('px-4 py-2', 'px-6');
    expect(result).toBe('py-2 px-6');
  });

  it('handles arrays of classes', () => {
    const result = cn(['class1', 'class2']);
    expect(result).toBe('class1 class2');
  });

  it('handles objects with boolean values', () => {
    const result = cn({
      base: true,
      active: true,
      disabled: false,
    });
    expect(result).toBe('base active');
  });

  it('handles empty input', () => {
    const result = cn();
    expect(result).toBe('');
  });

  it('handles mixed inputs', () => {
    const result = cn('base', ['array-class'], { 'object-class': true });
    expect(result).toBe('base array-class object-class');
  });
});

describe('formatDate', () => {
  it('formats date string correctly', () => {
    const date = '2024-01-15T10:30:00Z';
    const result = formatDate(date);
    
    // Should include month, day, year
    expect(result).toMatch(/Jan|January/);
    expect(result).toMatch(/15/);
    expect(result).toMatch(/2024/);
  });

  it('formats Date object correctly', () => {
    const date = new Date('2024-06-20T15:45:00Z');
    const result = formatDate(date);
    
    expect(result).toMatch(/Jun|June/);
    expect(result).toMatch(/20/);
    expect(result).toMatch(/2024/);
  });

  it('handles invalid date gracefully', () => {
    const result = formatDate('invalid-date');
    
    // Should return something (implementation dependent)
    expect(typeof result).toBe('string');
  });
});

describe('formatNumber', () => {
  it('formats small numbers with locale formatting', () => {
    const result = formatNumber(500);
    expect(result).toBe('500');
  });

  it('formats thousands with commas', () => {
    const result = formatNumber(1500);
    expect(result).toBe('1,500');
  });

  it('formats millions with commas', () => {
    const result = formatNumber(2500000);
    expect(result).toBe('2,500,000');
  });

  it('handles zero', () => {
    const result = formatNumber(0);
    expect(result).toBe('0');
  });

  it('handles negative numbers with commas', () => {
    const result = formatNumber(-1500);
    expect(result).toBe('-1,500');
  });
});

describe('formatCompactNumber', () => {
  it('formats small numbers without abbreviation', () => {
    const result = formatCompactNumber(500);
    expect(result).toBe('500');
  });

  it('formats thousands with K suffix', () => {
    const result = formatCompactNumber(1500);
    expect(result).toBe('1.5K');
  });

  it('formats millions with M suffix', () => {
    const result = formatCompactNumber(2500000);
    expect(result).toBe('2.5M');
  });

  it('handles zero', () => {
    const result = formatCompactNumber(0);
    expect(result).toBe('0');
  });

  it('rounds to one decimal place', () => {
    const result = formatCompactNumber(1234);
    expect(result).toBe('1.2K');
  });

  it('handles exact thousands', () => {
    const result = formatCompactNumber(1000);
    expect(result).toBe('1.0K');
  });

  it('handles exact millions', () => {
    const result = formatCompactNumber(1000000);
    expect(result).toBe('1.0M');
  });
});

