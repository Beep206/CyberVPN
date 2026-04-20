This is the standalone CyberVPN partner workspace.

## Getting Started

From the repo root:

```bash
npm run dev:partner
```

Or from `/partner` directly:

```bash
npm run dev
```

The partner app runs on [http://localhost:3002](http://localhost:3002) by default.

Set `NEXT_PUBLIC_SITE_URL` to match the active origin:

```bash
# local development
NEXT_PUBLIC_SITE_URL=http://localhost:3002

# production
NEXT_PUBLIC_SITE_URL=https://partner.ozoxy.ru
```

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
