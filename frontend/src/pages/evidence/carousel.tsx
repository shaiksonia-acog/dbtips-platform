import type React from "react"
import { useState } from "react"
import { Carousel as AntCarousel, Card, Row, Col, ConfigProvider, Empty, Typography } from "antd"
import { LinkOutlined } from "@ant-design/icons"

const { Paragraph, Text } = Typography

interface ImageData {
  url?: string
  pmcid?: string
  figtitle?: string
  figid?: string
  image_url?: string
  pmid?: string
  gene_symbols?: string[]
  drugs?: string
  keywords?: string
  process?: string
  insights?: string
  data_source?: string
}

interface CarouselProps {
  networkBiologyData: {
    results: ImageData[]
  }
}

const chunkImages = (images: ImageData[], chunkSize: number) => {
  const result: ImageData[][] = []
  for (let i = 0; i < images.length; i += chunkSize) {
    result.push(images.slice(i, i + chunkSize))
  }
  return result
}

const FlippableCard: React.FC<{ image: ImageData }> = ({ image }) => {
  const [isFlipped] = useState(false)

  const isPresent = (v?: string) => {
    if (!v) return false
    const s = v.trim().toLowerCase()
    return s.length > 0 && s !== "not mentioned"
  }
  const hasAnyAnalysis = isPresent(image.drugs) || isPresent(image.process) || isPresent(image.insights)

  const handleImageClick = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()

    const url =
      image.data_source === "network_biology"
        ? image.url
        : image.pmcid
          ? `https://pmc.ncbi.nlm.nih.gov/articles/${image.pmcid}`
          : image.pmid
            ? `https://pubmed.ncbi.nlm.nih.gov/${image.pmid}`
            : undefined

    if (url) {
      window.open(url, "_blank", "noopener,noreferrer")
    }
  }

  const renderBackContent = () => {
    return (
      <div className="card-back-content">
        {image.drugs && isPresent(image.drugs) && (
          <div className="mb-4">
            <Text strong className="text-blue-600 text-xs">
              Drugs:
            </Text>
            <Paragraph className="mt-1 mb-0 text-xs leading-relaxed text-justify">{image.drugs}</Paragraph>
          </div>
        )}
        {image.process && isPresent(image.process) && (
          <div className="mb-4">
            <Text strong className="text-green-600 text-xs">
              Process:
            </Text>
            <Paragraph className="mt-1 mb-0 text-xs leading-relaxed text-justify">{image.process}</Paragraph>
          </div>
        )}
        {image.insights && isPresent(image.insights) && (
          <div className="mb-2">
            <Text strong className="text-gray-700 text-xs">
              Insights:
            </Text>
            <Paragraph className="mt-1 mb-0 text-xs leading-relaxed text-justify">{image.insights}</Paragraph>
          </div>
        )}
      </div>
    )
  }

  return (
    <div
      className="flip-card"
      onClick={handleImageClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter") handleImageClick(e as any)
      }}
    >
      <div className={`flip-card-inner ${isFlipped ? "flipped" : ""}`}>
        {/* Front */}
        <div className="flip-card-front">
          <Card hoverable className="h-full relative" bodyStyle={{ padding: 0, height: "100%" }}>
            <div className="relative cursor-pointer h-[360px]">
              <img
                alt={image.figtitle}
                src={image.image_url || "/placeholder.svg?height=360&width=600&query=placeholder%20pathway%20figure"}
                className="w-full h-full object-contain bg-white rounded-t-lg block"
                decoding="async"
                fetchPriority="high"
                style={{
                  transform: "translateZ(0)",
                  WebkitTransform: "translateZ(0)",
                  WebkitBackfaceVisibility: "hidden",
                  backfaceVisibility: "hidden",
                }}
              />
              {image.data_source === "network_biology" && (
                <div className="absolute top-2 right-2 bg-white bg-opacity-90 rounded-full p-2">
                  <LinkOutlined className="text-blue-500" />
                </div>
              )}
            </div>

            <div className="absolute bottom-0 left-0 right-0 bg-white bg-opacity-95 backdrop-blur-sm p-2 rounded-b-lg">
              <div className="w-full">
                <Text className="text-black text-sm leading-tight hover:text-blue-600 transition-colors line-clamp-2 block">
                  <strong>{image.figtitle}</strong>
                </Text>
              </div>
            </div>
          </Card>
        </div>

        {/* Back */}
        {image.data_source === "network_biology" ? (
          <div className="flip-card-back">
            <Card className="h-full">
              <div className="card-back-content flex items-center justify-center text-center">
                <Paragraph className="text-xs text-gray-600 mb-0">
                  Analysis has not been generated for this figure because it comes from a different source (wikipathways).
                </Paragraph>
              </div>
            </Card>
          </div>
        ) : (
          <div className="flip-card-back">
            <Card className="h-full">
              {hasAnyAnalysis ? (
                renderBackContent()
              ) : (
                <div className="card-back-content flex items-center justify-center text-center">
                  <Paragraph className="text-xs text-gray-600 mb-0">
                    No additional analysis is available for this literature figure at the moment.
                  </Paragraph>
                </div>
              )}
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}

const ImageCarousel: React.FC<CarouselProps> = ({ networkBiologyData }) => {
  if (networkBiologyData && !networkBiologyData.results.length) {
    return <Empty />
  }

  const imageChunks =
    networkBiologyData && Array.isArray(networkBiologyData.results) ? chunkImages(networkBiologyData.results, 3) : []

  return (
    <>
      <style>{`
        /* 3D + compositing hints to avoid flicker on flip-back */
        .flip-card {
          background-color: transparent;
          width: 100%;
          height: 400px;
          perspective: 1200px; /* stronger perspective helps z ordering */
          isolation: isolate; /* new stacking context */
          cursor: pointer;
          contain: paint; /* reduce repaint scope */
        }

        .flip-card-inner {
          position: relative;
          width: 100%;
          height: 100%;
          text-align: center;
          transition: transform 0.6s;
          transform-style: preserve-3d;
          will-change: transform; /* keep on GPU */
        }

        .flip-card:hover .flip-card-inner {
          transform: rotateY(180deg);
        }

        .flip-card-front,
        .flip-card-back {
          position: absolute;
          width: 100%;
          height: 100%;
          -webkit-backface-visibility: hidden;
          backface-visibility: hidden;
          transform-style: preserve-3d;
        }

        /* Keep the front slightly in front to avoid z-fighting and keep texture alive */
        .flip-card-front {
          transform: rotateY(0deg) translateZ(1px);
          z-index: 2;
          will-change: transform;
        }

        .flip-card-back {
          transform: rotateY(180deg);
        }

        /* Apply backface rules and compositing to nested card elements and img */
        .flip-card-front .ant-card,
        .flip-card-front .ant-card-body,
        .flip-card-front img {
          -webkit-backface-visibility: hidden;
          backface-visibility: hidden;
          transform: translateZ(0);
          will-change: transform;
        }

        /* Enhanced caption styling - static, no hover effects since card flips on hover */
        .text-shadow-sm {
          text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
        }

        .card-back-content {
          padding: 12px;
          height: 100%;
          overflow-y: auto;
          text-align: left;
        }

        .line-clamp-2 {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .card-back-content::-webkit-scrollbar { width: 4px; }
        .card-back-content::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 2px; }
        .card-back-content::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 2px; }
        .card-back-content::-webkit-scrollbar-thumb:hover { background: #a8a8a8; }

        /* Keep image stable on hover (no extra transform) */
        .flip-card:hover .flip-card-front img { transform: translateZ(0); transition: none; }

        /* Text utilities */
        .text-justify { text-align: justify; word-wrap: break-word; hyphens: auto; }
        .card-back-content .ant-typography { margin-bottom: 0 !important; }
      `}</style>

      <ConfigProvider
        theme={{
          components: {
            Carousel: {
              arrowSize: 20,
              arrowOffset: 5,
            },
          },
        }}
      >
        <AntCarousel arrows infinite={false} dots={false}>
          {imageChunks.map((chunk, index) => (
            <div key={index}>
              <Row gutter={[16, 16]}>
                {chunk.map((image: ImageData, idx: number) => (
                  <Col key={idx} span={8}>
                    <FlippableCard image={image} />
                  </Col>
                ))}
              </Row>
            </div>
          ))}
        </AntCarousel>
      </ConfigProvider>
    </>
  )
}

export default ImageCarousel