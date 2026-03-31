import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { RouteNotFound } from '@/shared/ui/route-not-found';

export const metadata = withSiteMetadata(
  {
    title: 'Page Not Found | CyberVPN',
    description: 'The requested route is unavailable or not exposed on this VPN control surface.',
  },
  {
    routeType: 'private',
  },
);

export default function RootNotFound() {
  return <RouteNotFound />;
}
