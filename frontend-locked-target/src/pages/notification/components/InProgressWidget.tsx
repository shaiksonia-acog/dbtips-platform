/* eslint-disable @typescript-eslint/no-explicit-any */
import { Pagination } from "antd";
import {
  ChevronDown,
  ChevronRight,
  Loader2,
  Clock,
} from "lucide-react";
import { StatusTag } from "./StatusTag";
import { formatTime, renderDiseaseTarget } from "../utils";

export function InProgressWidget({
  combinedData,
  expandedRow,
  setExpandedRow,
  leftPage,
  setLeftPage,
  pageSize,
}: any) {
  const paginatedLeft = combinedData.slice(
    (leftPage - 1) * pageSize,
    leftPage * pageSize
  );

  return (
    <section
      className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden flex flex-col"
      aria-labelledby="left-statuses-heading"
    >
      <header className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200 px-6 py-5">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Loader2
              className={`h-5 w-5 text-blue-600 ${
                combinedData.length !== 0 ? "animate-spin" : ""
              }`}
              aria-hidden="true"
            />
          </div>
          <div>
            <h3
              id="left-statuses-heading"
              className="text-lg font-semibold text-gray-900"
            >
              In Progress
            </h3>
            <p className="text-sm text-gray-600">
              {combinedData.length} active dossiers
            </p>
          </div>
        </div>
      </header>

      <div className="divide-y divide-gray-100 overflow-y-auto flex-1">
        {paginatedLeft.length > 0 ? (
          paginatedLeft.map((d: any,index:number) => {
            const isExpandable =
              d.status === "processing" || d.status === "error";
            const isExpanded = expandedRow === d.id;

            return (
              <div
                key={index}
                className={`px-6 py-5 transition-all duration-200 ${
                  isExpandable
                    ? "hover:bg-gray-50 cursor-pointer"
                    : "hover:bg-gray-25"
                }`}
                onClick={() =>
                  isExpandable && setExpandedRow(isExpanded ? null : d.id)
                }
                role={isExpandable ? "button" : undefined}
                aria-expanded={isExpandable ? isExpanded : undefined}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    {isExpandable && (
                      <div className="mt-1">
                        {isExpanded ? (
                          <ChevronDown
                            className="h-4 w-4 text-gray-400 transition-transform duration-200"
                            aria-hidden="true"
                          />
                        ) : (
                          <ChevronRight
                            className="h-4 w-4 text-gray-400 transition-transform duration-200"
                            aria-hidden="true"
                          />
                        )}
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <h4 className="text-base font-semibold text-gray-900 mb-2 leading-tight">
                        {renderDiseaseTarget(d.disease, d.target)}
                      </h4>
                      <div className="flex items-center gap-2 text-sm text-gray-500">
                        <Clock className="h-4 w-4" />
                        <span>
                          Submitted {formatTime(d.creation_time)}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="ml-4">
                    <StatusTag status={d.status} />
                  </div>
                </div>

                {isExpanded && d.endpointStatus && (
                  <div className="mt-4 ml-7 p-4 bg-gray-50 rounded-lg border border-gray-100">
                    <h5 className="text-sm font-medium text-gray-700 mb-3">
                      Endpoint Progress
                    </h5>
                    <div className="flex gap-8 overflow-x-auto pb-2 divide-x divide-gray-300">
                      {Array.from(
                        {
                          length: Math.ceil(
                            Object.entries(d.endpointStatus).length / 5
                          ),
                        },
                        (_, colIndex) => (
                          <div
                            key={colIndex}
                            className={colIndex > 0 ? "pl-8" : ""}
                          >
                            {Object.entries(d.endpointStatus)
                              .slice(colIndex * 5, (colIndex + 1) * 5)
                              .map(([endpoint, statusObj]) => (
                                <div
                                  key={endpoint}
                                  className="flex justify-between items-center gap-4 py-2"
                                >
                                  <span className="text-sm text-gray-600 font-mono bg-gray-100 px-2 py-1 rounded whitespace-nowrap">
                                    {endpoint}
                                  </span>
                                  <StatusTag
                                    status={
                                      (statusObj as any)?.status ||
                                      "unknown"
                                    }
                                  />
                                </div>
                              ))}
                          </div>
                        )
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        ) : (
          <div className="px-6 py-16 text-center">
            <Loader2 className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 text-lg font-medium">
              No active dossiers
            </p>
            <p className="text-gray-400 text-sm mt-1">
              All submissions will appear here
            </p>
          </div>
        )}
      </div>

      {paginatedLeft.length > 0 && (
        <footer className="px-6 py-4 bg-gray-50 border-t border-gray-200">
          <Pagination
            current={leftPage}
            pageSize={pageSize}
            total={combinedData.length}
            onChange={setLeftPage}
            showSizeChanger={false}
            size="small"
            aria-label="In progress pagination"
            className="flex justify-center"
          />
        </footer>
      )}
    </section>
  );
}
