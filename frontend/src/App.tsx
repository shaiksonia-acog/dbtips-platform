import { useState, useEffect, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Spin, Layout, FloatButton } from 'antd';
import TargetIndication from './components/targetIndication';
import Header from './components/header';
import Footer from './components/footer';
import { parseQueryParams } from './utils/parseUrlParams';
import { ChatBot, useChatStore } from 'chatbot-component';
import ChatIcon from './assets/chat.svg?react';
import 'chatbot-component/dist/style.css';
import { config } from './utils/llmConfig';
import Notification from './pages/notification';
import Home from './pages/home';
import TargetProfile from './pages/target-profile';
import Literature from './pages/evidence';
import Data from './pages/data';
import Login from "./pages/login"
// import Search from "./components/search"
// import CoverLetter from './pages/coverLetter';
import Models from './pages/models';
import MarketIntelligence from './pages/market-intelligence';
import userAvatar from './assets/userAvatar.svg';
import assistantAvatar from "./assets/avatar3.jpg"
import TargetAssessment from './pages/target-assessment';
import DiseaseProfile from './pages/disease-profile';
import ProtectedRoute from './components/protectedRoute';
// import Genomics from "./pages/genomics"
// import ExportButton from './components/testExportButton';


// import { useQuery } from 'react-query';


const AppContent = () => {
   const [appState, setAppState] = useState({
       target: '',
       indications: [],
       data: [],
       loading: false,
       error: null,
   });


   const { isHidden, open, setConfig, } = useChatStore();


   useEffect(() => {
       setConfig(config);
   }, [setConfig]);


   useEffect(() => {
       const queryParams = new URLSearchParams(location.search);
       const { target, indications } = parseQueryParams(queryParams);


       setAppState((prevState) => ({
           ...prevState,
           target,
           indications,
       }));
   }, []);


   return (
       <Layout style={{ width: '100%',  }}>
           <Header app_state={appState} />
           <TargetIndication target={appState.target} indications={appState.indications} />


           <Layout
               hasSider={true}
               style={{ position: 'relative',  }}
           >
               <Layout.Content style={{ backgroundColor: 'white', overflow: 'auto' }}>
                   <main className=' min-h-[80vh]'>
                       <Suspense
                           fallback={
                               <div className='flex items-center justify-center h-[80vh]'>
                                   <Spin tip='loading...' />
                               </div>
                           }
                       >
                           <Routes>
   <Route path="/login" element={<Login />} />


   {/* Protected routes */}
   <Route
       path="/"
       element={
           <ProtectedRoute>
               <Home setAppState={setAppState} />
           </ProtectedRoute>
       }
   />
   <Route
       path="/target-biology"
       element={
           <ProtectedRoute>
               <TargetProfile />
           </ProtectedRoute>
       }
   />
   <Route
       path="/market-intelligence"
       element={
           <ProtectedRoute>
               <MarketIntelligence />
           </ProtectedRoute>
       }
   />
   <Route
       path="/disease-profile"
       element={
           <ProtectedRoute>
               <DiseaseProfile />
           </ProtectedRoute>
       }
   />
   <Route
       path="/literature"
       element={
           <ProtectedRoute>
               <Literature />
           </ProtectedRoute>
       }
   />
   <Route
       path="/data"
       element={
           <ProtectedRoute>
               <Data />
           </ProtectedRoute>
       }
   />
   <Route
       path="/target-assessment"
       element={
           <ProtectedRoute>
               <TargetAssessment />
           </ProtectedRoute>
       }
   />
   <Route
       path="/model-studies"
       element={
           <ProtectedRoute>
               <Models />
           </ProtectedRoute>
       }
   />
   <Route
       path="/notification"
       element={
           <ProtectedRoute>
               <Notification />
           </ProtectedRoute>
       }
   />
</Routes>


                       </Suspense>
                   </main>
               </Layout.Content>
               <Layout.Sider
                   width='30%'
                   className='min-w-[200px] bg-white overscroll-contain'
                   collapsible={true}
                   collapsedWidth={0}
                   collapsed={isHidden}
                   trigger={null}
                   style={{
                       // backgroundColor: '#fff',
                       zIndex: '100',
                       height: '90%',
                       marginBottom: '32px',
                       overflow: 'auto',
                   }}
               >
                   <div className='h-[100%] w-[30%] z-100 fixed pb-10 '>
                       <ChatBot baseURL='/llm' userAvatar={userAvatar} assistantAvatar={assistantAvatar} />
                   </div>
               </Layout.Sider>
           </Layout>
           {isHidden ? (
               <FloatButton
                   icon={<ChatIcon width={18} height={18} />}
                   onClick={open}
               />
           ) : null}
           <Footer />
       </Layout>
   );
};


const App = () => (
   <BrowserRouter>
       <AppContent />
   </BrowserRouter>
);


export default App;



