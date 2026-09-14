import ResetPasswordForm from "./reset-password-form";

type ResetPageProps = { searchParams: Promise<{ token?: string }> };

export default async function ResetPasswordPage({ searchParams }: ResetPageProps) {
  const { token = "" } = await searchParams;
  return <ResetPasswordForm initialToken={token} />;
}
