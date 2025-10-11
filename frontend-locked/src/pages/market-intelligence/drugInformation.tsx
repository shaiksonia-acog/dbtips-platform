import { Empty } from "antd";


export default function PublicAnalysis() {

  // Sentiment renderer with color coding and center alignment
 

  // Updated testimonials column definitions with increased row height and blue theme
 
  return (
    <div className="w-full px-[5vw] py-20" id="publicSentimentAnalysis">
      <h1 className="text-3xl font-semibold mb-1">Public sentiment analysis</h1>
      <p className="mt-2 font-medium mb-1">
        This section aggregates public sentiment and feedback to evaluate the market perception of approved drugs
        post-launch.
      </p>
      <div className="h-[40vh] flex items-center justify-center">
              <Empty description="Available on request" />
            </div>
    </div>
  )
}