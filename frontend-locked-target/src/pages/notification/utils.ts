import { capitalizeFirstLetter } from "../../utils/helper";

export const fetchData = async () => {
  const response = await fetch(
    `${import.meta.env.VITE_API_URI}/dossier/progression-tracker-dashboard/`
  );
  if (!response.ok) {
    throw new Error("Network response was not ok");
  }
  return response.json();
};

export const buildUrlWithIndications = (baseUrl: string, target: string, indications: string) => {
  const searchParams = new URLSearchParams();

  if (target) searchParams.set("target", target);
  if (indications && indications!== "no-disease") {
    const encodedIndications = `"${indications}"`;
    searchParams.set("indications", encodedIndications);
  }

  return `${baseUrl}?${searchParams.toString()}`;
};

export const formatTime = (timeString: string) => {
  if(!timeString) return "";
  const date = new Date(timeString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

export const formatStartTime = (timeString: string) => {
  if(!timeString) return "";
  const date = new Date(timeString);
  return (
    date.toLocaleDateString("en-US", { month: "short", day: "numeric" }) +
    ", " +
    date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
  );
};

export const calculateDuration = (startTime: string, endTime: string) => {
  const start = new Date(startTime);
  const end = new Date(endTime);
  const diffMins = Math.round((end.getTime() - start.getTime()) / (1000 * 60));
  if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? "s" : ""}`;
  const hours = Math.floor(diffMins / 60);
  const mins = diffMins % 60;
  return `${hours} hour${hours !== 1 ? "s" : ""}${
    mins > 0 ? ` ${mins} minute${mins !== 1 ? "s" : ""}` : ""
  }`;
};

export const renderDiseaseTarget = (disease?: string, target?: string) => {
  
  if (target && disease) {
    return disease === "no-disease"
      ? target?.toUpperCase()
      : `${target?.toUpperCase()} - ${capitalizeFirstLetter(disease)}`;
  }
  
  return target?.toUpperCase() || capitalizeFirstLetter(disease || "");
};

export const formatRelativeTime = (date: Date) => {
  const diffMs = new Date().getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? "s" : ""} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? "s" : ""} ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
};
