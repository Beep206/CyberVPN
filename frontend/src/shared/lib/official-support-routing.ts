export type OfficialSupportProfile = {
  surfaceLabel: string;
  supportLabel: string;
  supportEmail: string;
  responseWindow: string;
  helpCenterPath: string;
  communicationSenderName: string;
  communicationSenderEmail: string;
  legalPaths: {
    terms: string;
    privacy: string;
  };
};

export function getOfficialSupportProfile(): OfficialSupportProfile {
  return {
    surfaceLabel: 'CyberVPN Official Web',
    supportLabel: 'CyberVPN Customer Support',
    supportEmail: 'support@cybervpn.com',
    responseWindow: '24h',
    helpCenterPath: '/help',
    communicationSenderName: 'CyberVPN',
    communicationSenderEmail: 'support@cybervpn.com',
    legalPaths: {
      terms: '/terms',
      privacy: '/privacy',
    },
  };
}
