import { useNavigate } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';

interface Application {
  name: string;
  url: string;
  color: string;
  textColor: string;
}

function IndexPage() {
  const navigate = useNavigate();

  const generalApplications: Application[] = [
    { name: "Disease dossier", url: "/home", color: "bg-blue-100", textColor: "text-blue-800" },
    { name: "Target dossier", url: "https://dbtips-coe-target-dossier.own4.aganitha.ai:8443/", color: "bg-purple-100", textColor: "text-purple-800" },
  ];

  const specificApplications: Application[] = [
    { name: "Cancer Dossier", url: "https://dbtips-cancer-dossier.demos.aganitha.ai/", color: "bg-green-100", textColor: "text-green-800" },
    { name: "Migraine Dossier", url: "https://dbtips-mig.demos.aganitha.ai/", color: "bg-pink-100", textColor: "text-pink-800" },
    { name: "Ig-MOA-fit dossier", url: "https://ig-moa-fit.demos.aganitha.ai/", color: "bg-orange-100", textColor: "text-orange-800" },
    { name: "FA Dossier", url: "https://dbtips-fa.demos.aganitha.ai/", color: "bg-red-100", textColor: "text-red-800" },
    { name: "Immunological Disease Dossier", url: "https://dbtips-disease-dossier.demos.aganitha.ai/", color: "bg-yellow-100", textColor: "text-yellow-800" },
    { name: "Immunological Target Dossier", url: "https://dbtips-target-dossier.demos.aganitha.ai/", color: "bg-teal-100", textColor: "text-teal-800" },
  ];

  const handleClick = (app: Application) => {
    if (app.name === "Disease dossier") {
      navigate(app.url);
    }
  };

  const renderAppCard = (app: Application, index: number) => {
    const isInternal = app.name === "Disease dossier";

    const cardContent = (
      <div className={`relative rounded-2xl p-6 transition-all duration-500 animate-slide-up
        ${app.color}
        hover:scale-105 hover:shadow-xl hover:shadow-black/5
        hover:-translate-y-2 cursor-pointer
        border border-black/5`}>
        <div className="absolute inset-0 bg-black/5 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>

        <div className="relative">
          <div className="flex items-center justify-between mb-4">
            <h2 className={`text-2xl font-bold ${app.textColor} group-hover:opacity-90 transition-colors duration-300`}>
              {app.name}
            </h2>
            <ArrowUpRight className={`w-6 h-6 ${app.textColor} opacity-70 group-hover:opacity-100 
              transform group-hover:-translate-y-1 group-hover:translate-x-1 
              transition-all duration-300 ease-out`} />
          </div>

          <div className="mt-4">
            <span className={`text-sm ${app.textColor} opacity-70 group-hover:opacity-90 transition-colors duration-300`}>
              Launch application
            </span>
          </div>
        </div>
      </div>
    );

    return isInternal ? (
      <div key={index} onClick={() => handleClick(app)} className="group">
        {cardContent}
      </div>
    ) : (
      <a
        key={index}
        href={app.url}
        target="_blank"
        rel="noopener noreferrer"
        className="group"
        style={{ animationDelay: `${index * 100}ms` }}
      >
        {cardContent}
      </a>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-5xl font-bold text-gray-900 mb-2 text-center animate-fade-in">
          Application Directory
        </h1>
        <p className="text-gray-600 text-center mb-12">Select an application to get started</p>

        <h2 className="text-2xl font-semibold text-gray-800 mb-4">General Dossiers</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {generalApplications.map(renderAppCard)}
        </div>

        <h2 className="text-2xl font-semibold text-gray-800 mb-4">Specific Dossiers</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {specificApplications.map(renderAppCard)}
        </div>
      </div>
    </div>
  );
}

export default IndexPage;
