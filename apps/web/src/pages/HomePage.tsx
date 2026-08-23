import { Button, Card } from "../lib/components";

export const HomePage = () => {

  // Three quick-start repo cards per design spec
  const quickStartCards = [
    {
      name: "synthetic-minimal",
      title: "Quick Start",
      description: "Analyze a minimal repository in seconds",
    },
    {
      name: "synthetic-mature",
      title: "Best Practices",
      description: "Evaluate code health against 8 quality dimensions",
    },
    {
      name: "synthetic-evolution",
      title: "Evolution",
      description: "Track software evolution over time",
    },
  ];

  return (
    <div className="min-h-screen bg-pageBg">
      {/* Hero Section */}
      <header className="pt-8 pb-6">
        <h1 className="text-4xl font-bold text-slate-700 mb-2">
          <span className="text-lavenderPrimary">Project</span> DNA
        </h1>
        <p className="text-lavender-soft text-lg mb-6">
          Software archaeology & project intelligence platform
        </p>
        <Button className="cta-primary">Start Analysis</Button>
      </header>

      {/* Quick Start Repo Cards */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold text-slate-700 mb-4">Quick Start</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {quickStartCards.map((card) => (
            <Card
              key={card.name}
              className="p-6 hover:shadow-md transition-shadow"
            >
              <div className="w-12 h-12 rounded-md bg-lavenderSoft flex items-center justify-center flex-shrink-0">
                <span className="text-lavenderPrimary font-medium">{card.name.slice(0, 3)}</span>
              </div>
              <div className="ml-4">
                <h3 className="font-medium text-lavenderPrimary">{card.title}</h3>
                <p className="text-slate-500 mt-1">{card.description}</p>
              </div>
            </Card>
          ))}
        </div>
      </section>

      {/* Feature Highlights */}
      <section>
        <h2 className="text-2xl font-bold text-slate-700 mb-6">Key Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="p-4">
            <h4 className="font-medium text-lavenderPrimary mb-2">8-Dimensional Scoring</h4>
            <p className="text-slate-500">Analyze technical complexity, maintainability, testing maturity, and more</p>
          </Card>
          <Card className="p-4">
            <h4 className="font-medium text-lavenderPrimary mb-2">OAuth Integration</h4>
            <p className="text-slate-500">Connect GitHub for repository intelligence</p>
          </Card>
          <Card className="p-4">
            <h4 className="font-medium text-lavenderPrimary mb-2">CI/CD Ready</h4>
            <p className="text-slate-500">Built for automated analysis and reporting</p>
          </Card>
        </div>
      </section>
    </div>
  );
};

export default HomePage;