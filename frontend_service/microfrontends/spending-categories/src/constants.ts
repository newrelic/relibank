/**
 * New Relic Microfrontend Configuration
 *
 * This UUID must remain stable across deployments to maintain entity identity in New Relic.
 * Generate once using: uuidgen or https://www.uuidgenerator.net/
 */
export const SPENDING_CATEGORIES_MFE_CONFIG = {
  id: '750e8400-e29b-41d4-a716-446655440002',
  name: 'Spending Categories MFE',
  version: '1.0.0',
  tags: {
    team: 'dashboard',
    type: 'visualization',
    feature: 'spending-categories'
  }
} as const;
