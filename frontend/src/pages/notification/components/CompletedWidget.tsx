/* eslint-disable @typescript-eslint/no-explicit-any */
import { Pagination } from "antd";
import {
  CheckCircle,
  Clock,
} from "lucide-react";
import { Link } from "react-router-dom";
import { StatusTag } from "./StatusTag";
import { buildUrlWithIndications, calculateDuration, formatStartTime, renderDiseaseTarget } from "../utils";

export function CompletedWidget({
  processedData,
  rightPage,
  setRightPage,
  pageSize,
}: any) {
  console.log("processedData", processedData);
  const paginatedRight = processedData.slice(
    (rightPage - 1) * pageSize,
    rightPage * pageSize
  );
console.log("paginatedRight", paginatedRight);
  return (
    <section
      className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden flex flex-col"
      aria-labelledby="ready-heading"
    >
      <header className="bg-gradient-to-r from-green-50 to-emerald-50 border-b border-gray-200 px-6 py-5">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-green-100 rounded-lg">
            <CheckCircle
              className="h-5 w-5 text-green-600"
              aria-hidden="true"
            />
          </div>
          <div>
            <h3
              id="ready-heading"
              className="text-lg font-semibold text-gray-900"
            >
              Completed
            </h3>
            <p className="text-sm text-gray-600">
              {processedData.length} ready dossiers
            </p>
          </div>
        </div>
      </header>

      <div className="divide-y divide-gray-100 overflow-y-auto flex-1">
        {paginatedRight.length > 0 ? (
          paginatedRight.map((d: any, index: number) => (
            <div
              key={`${index}`}
              className="px-6 py-5 hover:bg-gray-50 transition-colors duration-200 cursor-pointer group"
            >
              <div className="flex items-start justify-between mb-2">
                <Link
                  to={buildUrlWithIndications("/", d.target, d.disease)}
                  className="flex items-center gap-x-2 hover:text-black "
                >
                  <h4 className="text-base font-semibold text-gray-900 group-hover:text-blue-600 transition-colors duration-200 leading-tight">
                    {renderDiseaseTarget(d.disease, d.target)}
                  </h4>
                </Link>
                <StatusTag status="processed" />
              </div>

              <div className="space-y-1 flex justify-between">
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <Clock className="h-4 w-4" />
                  <span>Started {formatStartTime(d.submission_time)}</span>
                </div>

                <div className="flex items-center gap-2 text-sm">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span className="text-green-700 font-medium">
                    Completed in{" "}
                    {calculateDuration(d.submission_time, d.processed_time)}
                  </span>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="px-6 py-16 text-center">
            <CheckCircle className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 text-lg font-medium">
              No completed dossiers
            </p>
            <p className="text-gray-400 text-sm mt-1">
              Finished analyses will appear here
            </p>
          </div>
        )}
      </div>

      {paginatedRight.length > 0 && (
        <footer className="px-6 py-4 bg-gray-50 border-t border-gray-200">
          <Pagination
            current={rightPage}
            pageSize={pageSize}
            total={processedData.length}
            onChange={setRightPage}
            showSizeChanger={false}
            size="small"
            aria-label="Completed pagination"
            className="flex justify-center"
          />
        </footer>
      )}
    </section>
  );
}
