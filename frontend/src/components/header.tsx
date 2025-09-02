import { useState, useEffect } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { Dropdown } from "antd";
import AganithaLogo from "../assets/aganitha-logo.png";
import UserDropdown from "./userDropdown";


const Header = ({ app_state }) => {
 const location = useLocation();
 const navigate = useNavigate();
 const [email, setEmail] = useState<string>("");
 const [showNavMenu, setShowNavMenu] = useState(true);
 const [selectedKey, setSelectedKey] = useState(null);
 const handleLogout = async () => {
   try {
     // Call the logout endpoint to clean up server-side session
     const response = await fetch(`${import.meta.env.VITE_API_URI}/logout`, {
       method: "POST",
       headers: {
         "Content-Type": "application/json",
       },
     });
      if (response.ok) {
       window.location.replace("/login");
     } else {
       // Even if server call fails, still clear cookie and redirect
       console.error("Server logout failed, clearing cookie locally");
     }
   } catch (error) {
     // Network error - still clear cookie and redirect
     console.error("Logout request failed:", error);
     document.cookie = "session_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
     window.location.replace("/login");
   }
 };
 useEffect(() => {
   const fetchUser = async () => {
     try {
       const res = await fetch(`${import.meta.env.VITE_API_URI}/me`, {
         credentials: "include", // send session cookie
       });
       if (res.ok) {
         const data = await res.json();
         const email = data?.email ||data?.user;
         setEmail(email);
       } else {
         setEmail("");
       }
     } catch (err) {
       console.error("Failed to fetch user:", err);
     }
   };


   fetchUser();
 }, []);


 // Menu groups
 const targetMenuItems = [
   {
     key: "target-biology",
     label: "Target Overview",
     children: [
       { key: "target-description", label: "Target description" },
       { key: "taxonomy", label: "Taxonomy" },
       { key: "ontology", label: "Ontology" },
       { key: "protein-expression", label: "RNA/Protein expressions" },
       { key: "protein-structure", label: "Protein structure" },
       { key: "sub-cellular-location", label: "Subcellular localization" },
     ],
   },
   {
     key: "market-intelligence",
     label: "Market Intelligence",
     children: [
       { key: "approvedDrug", label: "Approved drugs" },
       { key: "pipeline-by-target", label: "Therapeutic pipeline" },
       { key: "patent", label: "Patents" },
     ],
   },


   {
     key: "literature",
     label: "Evidence",
     children: [
       { key: "literature-evidence", label: "Literature" },
       { key: "model-studies", label: "Target perturbation phenotypes" },
     ],
   },
 
   {
     key: "target-assessment",
     label: "Target Assessment",
     children: [
       { key: "targetability", label: "Targetability" },
       { key: "tractability", label: "Tractability" },
       { key: "paralogs", label: "Paralogs" },
       { key: "geneEssentialityMap", label: "Gene essentiality map" },
     ],
   },
 ];


 const diseaseMenuItems = [
   {
     key: "disease-profile",
     label: "Disease Overview",
     disabled: false,
     children: [
       {
         key: `disease-description`,
         label: `Description`,
       },
       {
         key: `disease-ontology`,
         label: `Ontology`,
       },
       {
         label: "Diagnostics and Biomarkers",
         key: "diagnostics",
         children: [
           {
             key: "GTR",
             label: "Genetic Testing Registry",
           },
           {
             key: "biomarkers",
             label: "Biomarkers",
             disabled: true,
           },
         ],
       },
     ],
   },


   {
     key: "market-intelligence",
     label: "Market Intelligence",
     children: [
       { key: "approvedDrug", label: "Approved drugs" },
       { key: "pipeline-by-indications", label: "Therapeutic pipeline" },
       {
         key: "opinionLeaders",
         label: "Opinion leaders",
         children: [
           { key: "siteInvetigators", label: "Site investigators" },


           { key: "kol", label: "Key influential leaders" },
           //   { key: 'kol', label: 'Key researchers' },
         ],
       },
       {
         key: "patientStories",
         label: "Patient stories",
       },
       {
         key: "patientAdvocacyGroup",
         label: "Patient advocacy groups",
       },
     ],
   },
   {
     key: "data",
     label: "Data",
     children: [
       {
         key: "rnaSeq",
         label: "RNA-seq datasets",
       },
       {
         key: "GenomicsStudies",
         label: "Genomics studies",
         children: [
           {
             key: "gwasStudies",
             label: "GWAS studies",
           },
           {
             key: "manhattanPlot",
             label: "Manhattan plot/Locuszoom",
           },
           {
             key: "pgsCatalog",
             label: "Polygenic risk scores",
           },
         ],
       },
     ],
   },
   {
     key: "literature",
     label: "Literature ",
     children: [
       {
         key: "literature-evidence",
         label: "Literature reviews",
       },
       {
         key: "knowledge-graph-evidence",
         label: "Disease pathways",
       },
     ],
   },


   {
     key: "model-studies",
     label: "Models",
     children: [
       {
         key: "model-studies",
         label: "Animal models ",
       },
     ],
   },
 ];


 const bothMenuItems = [
   {
     key: "target-biology",
     label: "Target Overview",
     children: [
       {
         key: "target-description",
         label: "Target description",
       },
       {
         key: "taxonomy",
         label: "Taxonomy",
       },
       {
         key: "ontology",
         label: "Ontology",
       },
       {
         key: "protein-expression",
         label: "RNA/Protein expressions",
       },
       {
         key: "protein-structure",
         label: "Protein structure",
       },
       {
         key: "sub-cellular-location",
         label: "Subcellular localization",
       },
     ],
   },


   {
     key: "disease-profile",
     label: "Disease Overview",
     disabled: false,
     children: [
       {
         key: `disease-description`,
         label: `Description`,
       },
       {
         key: `disease-ontology`,
         label: `Ontology`,
       },
       {
         label: "Diagnostics and Biomarkers",
         key: "diagnostics",
         children: [
           {
             key: "GTR",
             label: "Genetic Testing Registry",
           },
           {
             key: "biomarkers",
             label: "Biomarkers",
             disabled: true,
           },
         ],
       },
     ],
   },


   {
     key: "market-intelligence",
     label: "Market Intelligence",
     children: [
       { key: "approvedDrug", label: "Approved drugs" },
       { key: "pipeline-by-target", label: "Therapeutic pipeline" },
       { key: "patent", label: "Patents" },
     ],
   },
   {
     key: "data",
     label: "Data",
     children: [
       {
         key: "rnaSeq",
         label: "RNA-seq datasets",
       },
       {
         key: "GenomicsStudies",
         label: "Genomics studies",
         children: [
           {
             key: "gwasStudies",
             label: "GWAS studies",
           },
           {
             key: "manhattanPlot",
             label: "Manhattan plot/Locuszoom",
           },
           {
             key: "pgsCatalog",
             label: "Polygenic risk scores",
           },
         ],
       },
     ],
   },


   {
     key: "literature",
     label: "Evidence",
     children: [
       { key: "literature-evidence", label: "Literature" },


       {
         key: "knowledge-graph-evidence",
         label: "Disease pathways",
       },
       {
         key: "model-studies",
         label: "Target perturbation phenotypes",
       },
     ],
   },


   {
     key: "model-studies",
     label: "Models",
     children: [
       {
         key: "model-studies",
         label: "Animal models ",
       },
     ],
   },
   {
     key: "target-assessment",
     label: "Target Assessment",
     children: [
       {
         key: "targetability",
         label: "Targetability",
       },
       {
         key: "tractability",
         label: "Tractability",
       },
       {
         key: "paralogs",
         label: "Paralogs",
       },
       {
         key: "geneEssentialityMap",
         label: "Gene essentiality map",
       },
     ],
   },
 ];


 // Select menu items based on state
 let menuItems = [];
 const hasTarget = !!app_state.target;
 const hasIndications =
   app_state.indications && app_state.indications.length > 0;


 if (hasTarget && hasIndications) {
   menuItems = [...bothMenuItems];
 } else if (hasTarget) {
   menuItems = targetMenuItems;
 } else if (hasIndications) {
   menuItems = diseaseMenuItems;
 }


 // Toggle nav visibility based on current route
 useEffect(() => {
   setShowNavMenu(
     !(location.pathname === "/" || location.pathname === "/home")
   );
 }, [location]);


 const scrollIntoView = (id) => {
   const section = document.getElementById(id);
   if (!section) return;
   const headerOffset = location.pathname === "/" ? 60 : 130;
   const elementPosition = section.getBoundingClientRect().top;
   const offsetPosition = elementPosition + window.scrollY - headerOffset;


   window.scrollTo({ top: offsetPosition, behavior: "smooth" });
 };


 const navigateWithParams = (path, key) => {
   const target = app_state.target || "";
   const indications = (app_state.indications || [])
     .map((indication) => `"${indication}"`)
     .join(",");
   navigate(`${path}?target=${target}&indications=${indications}`);
   setTimeout(() => scrollIntoView(key), 250);
 };


 const buildUrlWithIndications = (baseUrl, target, indications) => {
   const searchParams = new URLSearchParams();
   if (target) searchParams.set("target", target);
   if (indications?.length) {
     const encodedIndications = indications.map((i) => `"${i}"`).join(",");
     searchParams.set("indications", encodedIndications);
   }
   return `${baseUrl}?${searchParams.toString()}`;
 };


 const handlePressEffect = (e) => {
   e.target.classList.add("pressed");
   setTimeout(() => e.target.classList.remove("pressed"), 300);
 };


 return (
   <header className="border-b sticky top-0 z-10 bg-white pl-[5vw] py-4">
     <div className="flex items-center justify-between">
       <Link
         to={buildUrlWithIndications(
           "/",
           app_state.target,
           app_state.indications
         )}
         className="flex items-center gap-x-2 hover:text-black "
       >
         <img width={90} src={AganithaLogo} alt="Aganitha" />
         <div className="w-[1px] h-4 bg-[#555]" />
         <h2 className="text-base">
           DBTIPS<sup>TM</sup> - Disease & Target Dossier
         </h2>
       </Link>


       {showNavMenu ? (
         <nav className="flex items-center px-2 mr-5 gap-1">
           {menuItems.map((page, index) => (
             <div key={index}>
               <Dropdown
                 menu={{
                   items: page.children || [],
                   onClick: (e) => {
                     setSelectedKey(e.key);
                     if (page.key !== location.key) {
                       navigateWithParams(`/${page.key}`, e.key);
                     } else {
                       scrollIntoView(e.key);
                     }
                   },
                   selectable: true,
                   selectedKeys: [selectedKey],
                 }}
               >
                 {page.disabled ? (
                   <span className="text-base cursor-not-allowed text-zinc-400">
                     {page.label}
                   </span>
                 ) : (
                   <NavLink
                     to={buildUrlWithIndications(
                       `/${page.key}`,
                       app_state.target,
                       app_state.indications
                     )}
                     className={"nav-link"}
                     onMouseDown={handlePressEffect}
                   >
                     <span className="flex items-center">
                       <span className="text-base px-2 border-gray-200">
                         {page.label}
                         {page.children && (
                           <span className="material-symbols-outlined text-2xl align-middle">
                             arrow_drop_down
                           </span>
                         )}
                       </span>
                     </span>
                   </NavLink>
                 )}
               </Dropdown>
               <div style={{ display: "flex", justifyContent: "flex-end", padding: "0 16px" }}>
     {email && <UserDropdown email={email} onLogout={handleLogout} />}
   </div>
             </div>
            
           ))}
         </nav>
        
       ):
       <div>
             <div style={{ display: "flex", justifyContent: "flex-end", padding: "0 16px" }}>
     {email && <UserDropdown email={email} onLogout={handleLogout} />}
   </div>


       </div>
       }
     </div>
   </header>
 );
};


export default Header;



