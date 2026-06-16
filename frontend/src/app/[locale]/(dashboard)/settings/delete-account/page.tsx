import { DeleteAccountClient } from '@/widgets/delete-account/delete-account-client';

export default function SettingsDeleteAccountPage() {
  return (
    <div className="mx-auto w-full max-w-5xl">
      <DeleteAccountClient cancelHref="/settings" returnHref="/settings" surface="cabinet" />
    </div>
  );
}
