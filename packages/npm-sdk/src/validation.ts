/**
 * Validation utilities to prevent accidental nginx configuration breaks
 * and injection attacks when user input is passed through the SDK.
 */

/**
 * Validates advanced_config to prevent patterns that would break nginx configuration.
 * This provides basic protection against common mistakes and injection attacks.
 */
export function validateAdvancedConfig(config: string | undefined): void {
  if (!config || config.trim() === '') {
    return;
  }

  const breakoutPatterns = [
    { pattern: /}\s*server\s*{/i, message: 'Closing and opening server blocks would break NPM configuration' },
    { pattern: /}\s*http\s*{/i, message: 'Closing and opening http blocks would break NPM configuration' },
  ];

  for (const { pattern, message } of breakoutPatterns) {
    if (pattern.test(config)) {
      throw new Error(`Invalid advanced_config: ${message}`);
    }
  }
}

/**
 * Validates domain names to prevent characters that would break nginx configuration.
 *
 * Supports:
 * - Standard domains: example.com, sub.example.com
 * - Wildcards: *.example.com
 * - Single-label: localhost, myserver
 * - IP addresses: 192.168.1.1
 * - Unicode/IDN domains (if already in ASCII/punycode form)
 */
export function validateDomainNames(domains: string[] | undefined): void {
  if (!domains || domains.length === 0) {
    return;
  }

  for (const domain of domains) {
    if (!domain || domain.trim() === '') {
      throw new Error('Domain name cannot be empty');
    }

    if (/[\s;{}]/.test(domain)) {
      throw new Error(
        `Invalid domain name: "${domain}" contains characters that would break nginx configuration (spaces, semicolons, or braces)`
      );
    }

    if (domain.length > 253) {
      throw new Error(`Domain name too long: "${domain}" (max 253 characters)`);
    }
  }
}
