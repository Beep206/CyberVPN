export type OfficialSupportProfile = {
  surfaceLabel: string;
  supportLabel: string;
  supportEmail: string;
  refundEmail: string;
  responseWindow: string;
  helpCenterPath: string;
  webTicketPath: string;
  telegramBotUrl: string;
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
    supportEmail: 'support@cyber-vpn.net',
    refundEmail: 'refund@cyber-vpn.net',
    responseWindow: '<=12h beta first response',
    helpCenterPath: '/help',
    webTicketPath: '/contact',
    telegramBotUrl: 'https://t.me/cybervpn_bot',
    communicationSenderName: 'CyberVPN',
    communicationSenderEmail: 'support@cyber-vpn.net',
    legalPaths: {
      terms: '/terms',
      privacy: '/privacy',
    },
  };
}
