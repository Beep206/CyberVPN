import { Suspense } from 'react';
import { connection } from 'next/server';
import { ForgotPasswordClient } from './forgot-password-client';

export default async function ForgotPasswordPage() {
  await connection();

  return (
    <Suspense fallback={null}>
      <ForgotPasswordClient />
    </Suspense>
  );
}
