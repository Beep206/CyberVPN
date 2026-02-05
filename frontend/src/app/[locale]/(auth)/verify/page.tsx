import { OtpVerificationForm } from '@/features/auth/components';
import { useTranslations } from 'next-intl';

export default function VerifyPage() {
    return (
        <div className="min-h-[80vh] flex flex-col items-center justify-center p-4">
            <OtpVerificationForm />
        </div>
    );
}
