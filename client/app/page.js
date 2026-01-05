import Link from "next/link";

export default function Home() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <main className="flex flex-col items-center justify-center px-6 py-12 text-center">
        {/* Hero Section */}
        <div className="mb-8">
          <div className="mb-6 inline-block rounded-2xl bg-gradient-to-r from-blue-600 to-purple-600 p-4 shadow-xl">
            <svg
              className="h-12 w-12 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
          </div>
        </div>

        <h1 className="mb-4 text-5xl font-bold tracking-tight text-gray-900 dark:text-white md:text-6xl">
          Email Integration
        </h1>
        
        <p className="mb-8 max-w-2xl text-xl text-gray-600 dark:text-gray-300">
          Seamlessly manage your email communications with our powerful integration platform.
          Connect, organize, and streamline your workflow.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col gap-4 sm:flex-row sm:gap-6">
          <Link
            href="/auth/signup"
            className="group relative inline-flex items-center justify-center overflow-hidden rounded-full bg-gradient-to-br from-blue-600 to-purple-600 px-8 py-4 text-lg font-semibold text-white shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-2xl"
          >
            <span className="relative">Get Started</span>
            <svg
              className="ml-2 h-5 w-5 transition-transform group-hover:translate-x-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 7l5 5m0 0l-5 5m5-5H6"
              />
            </svg>
          </Link>

          <Link
            href="/auth/login"
            className="inline-flex items-center justify-center rounded-full border-2 border-gray-300 bg-white px-8 py-4 text-lg font-semibold text-gray-900 shadow-md transition-all duration-300 hover:scale-105 hover:border-blue-600 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:hover:border-purple-500 dark:hover:bg-gray-700"
          >
            Sign In
          </Link>
        </div>

        {/* Features */}
        <div className="mt-20 grid max-w-5xl gap-8 sm:grid-cols-3">
          <div className="rounded-2xl bg-white p-6 shadow-lg transition-all duration-300 hover:scale-105 dark:bg-gray-800">
            <div className="mb-4 inline-block rounded-full bg-blue-100 p-3 dark:bg-blue-900">
              <svg
                className="h-6 w-6 text-blue-600 dark:text-blue-300"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
            </div>
            <h3 className="mb-2 text-xl font-semibold text-gray-900 dark:text-white">
              Fast & Secure
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              Lightning-fast email processing with enterprise-grade security
            </p>
          </div>

          <div className="rounded-2xl bg-white p-6 shadow-lg transition-all duration-300 hover:scale-105 dark:bg-gray-800">
            <div className="mb-4 inline-block rounded-full bg-purple-100 p-3 dark:bg-purple-900">
              <svg
                className="h-6 w-6 text-purple-600 dark:text-purple-300"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
                />
              </svg>
            </div>
            <h3 className="mb-2 text-xl font-semibold text-gray-900 dark:text-white">
              Customizable
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              Tailor your email workflow to match your unique needs
            </p>
          </div>

          <div className="rounded-2xl bg-white p-6 shadow-lg transition-all duration-300 hover:scale-105 dark:bg-gray-800">
            <div className="mb-4 inline-block rounded-full bg-green-100 p-3 dark:bg-green-900">
              <svg
                className="h-6 w-6 text-green-600 dark:text-green-300"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
            </div>
            <h3 className="mb-2 text-xl font-semibold text-gray-900 dark:text-white">
              Reliable
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              99.9% uptime with 24/7 monitoring and support
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
