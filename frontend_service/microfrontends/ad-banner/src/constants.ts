/**
 * New Relic Microfrontend Configuration
 *
 * This UUID must remain stable across deployments to maintain entity identity in New Relic.
 * Generate once using: uuidgen or https://www.uuidgenerator.net/
 */
export const AD_BANNER_MFE_CONFIG = {
  id: '550e8400-e29b-41d4-a716-446655440000',
  name: 'Ad Banner MFE',
  version: '1.0.0',
  tags: {
    team: 'marketing',
    type: 'promotion',
    feature: 'rewards-signup'
  }
} as const;
