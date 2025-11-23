import Link from 'next/link'
import { ArrowRight, Shield, ScanSearch, Zap, Lock } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">SecDash</span>
          </div>
          <nav className="flex items-center gap-6">
            <Link
              href="/login"
              className="text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
            >
              Login
            </Link>
            <Link
              href="/signup"
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              Get Started
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1">
        <section className="container py-24 md:py-32">
          <div className="mx-auto max-w-4xl text-center">
            <h1 className="mb-6 text-4xl font-bold tracking-tight sm:text-6xl">
              Secure Your Code,{' '}
              <span className="text-primary">Protect Your Future</span>
            </h1>
            <p className="mb-8 text-lg text-muted-foreground sm:text-xl">
              Comprehensive security scanning for all your repositories.
              Detect vulnerabilities, secrets, and code quality issues with AI-powered analysis.
            </p>
            <div className="flex flex-col gap-4 sm:flex-row sm:justify-center">
              <Link
                href="/dashboard"
                className="inline-flex items-center justify-center rounded-md bg-primary px-8 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
              >
                Go to Dashboard
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
              <Link
                href="/docs"
                className="inline-flex items-center justify-center rounded-md border border-input bg-background px-8 py-3 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground"
              >
                View Documentation
              </Link>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="border-t bg-muted/50 py-24">
          <div className="container">
            <div className="mx-auto max-w-2xl text-center mb-16">
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
                Comprehensive Security Scanning
              </h2>
              <p className="mt-4 text-lg text-muted-foreground">
                Multiple security tools integrated into one powerful platform
              </p>
            </div>

            <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-4">
              <FeatureCard
                icon={<ScanSearch className="h-10 w-10" />}
                title="SAST Scanning"
                description="Static analysis with Semgrep, Bandit, and ESLint to catch vulnerabilities early"
              />
              <FeatureCard
                icon={<Shield className="h-10 w-10" />}
                title="Dependency Checks"
                description="Scan dependencies with Trivy and OWASP Dependency-Check for known vulnerabilities"
              />
              <FeatureCard
                icon={<Lock className="h-10 w-10" />}
                title="Secret Detection"
                description="Find exposed secrets and credentials with Gitleaks before they leak"
              />
              <FeatureCard
                icon={<Zap className="h-10 w-10" />}
                title="AI-Powered Analysis"
                description="Get intelligent insights and fix suggestions from local LLM models"
              />
            </div>
          </div>
        </section>

        {/* Stats Section */}
        <section className="container py-24">
          <div className="grid gap-8 sm:grid-cols-3">
            <StatCard value="10,000+" label="Vulnerabilities Detected" />
            <StatCard value="500+" label="Repositories Scanned" />
            <StatCard value="99.9%" label="Uptime" />
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t py-6">
        <div className="container flex flex-col items-center justify-between gap-4 sm:flex-row">
          <p className="text-sm text-muted-foreground">
            © 2024 SecDash. Built with Next.js and FastAPI.
          </p>
          <div className="flex gap-4">
            <Link
              href="/privacy"
              className="text-sm text-muted-foreground hover:text-primary"
            >
              Privacy
            </Link>
            <Link
              href="/terms"
              className="text-sm text-muted-foreground hover:text-primary"
            >
              Terms
            </Link>
          </div>
        </div>
      </footer>
    </div>
  )
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="rounded-lg border bg-card p-6 text-card-foreground">
      <div className="mb-4 text-primary">{icon}</div>
      <h3 className="mb-2 text-lg font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  )
}

function StatCard({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-lg border bg-card p-8 text-center">
      <div className="text-4xl font-bold text-primary">{value}</div>
      <div className="mt-2 text-sm text-muted-foreground">{label}</div>
    </div>
  )
}
