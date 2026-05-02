import { Suspense } from 'react';
import { OtpVerificationForm } from '@/features/auth/components';

export default function VerifyPage() {
    return (
        <div className="min-h-[80vh] flex flex-col items-center justify-center p-4">
            <Suspense fallback={null}>
                <OtpVerificationForm />
            </Suspense>
        </div>
    );
}
