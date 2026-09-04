import { formatName } from './utils.js';

export function formatGreeting(first: string, last: string): string {
  return `Welcome, ${formatName(first, last)}!`;
}
