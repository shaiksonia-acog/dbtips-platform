/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useRef, useState } from "react";
import {
  Carousel,
  Card,
  Row,
  Col,
  ConfigProvider,
  Empty,
  Modal,
} from "antd";
import { ExternalLinkIcon } from "lucide-react";
import { CarouselRef } from "antd/es/carousel";

const isPresent = (val: any) => val !== null && val !== undefined && val !== "";

const chunkImages = (images: any[], chunkSize: number) => {
  const result: any[][] = [];
  for (let i = 0; i < images.length; i += chunkSize) {
    result.push(images.slice(i, i + chunkSize));
  }
  return result;
};

const CarouselComponent = ({ networkBiologyData,currentPage = 1,onSlideChange }) => {
  const carouselRef = useRef<CarouselRef>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedImage, setSelectedImage] = useState<any>(null);
  const [internalSlide, setInternalSlide] = useState(currentPage - 1);

  useEffect(() => {
    const targetIndex = currentPage - 1;
    if (carouselRef.current && targetIndex !== internalSlide) {
      carouselRef.current.goTo(targetIndex, false);
      setInternalSlide(targetIndex);
    }
  }, [currentPage, internalSlide]);

 
  const imageChunks =
    networkBiologyData && Array.isArray(networkBiologyData.results)
      ? chunkImages(networkBiologyData.results, 3)
      : [];

  const handleInfoClick = (image: any, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setSelectedImage(image);
    setIsModalOpen(true);
  };
  if (networkBiologyData && !networkBiologyData.results.length) {
    return <Empty />;
  }

  return (
    <>
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
        <Carousel infinite={false} arrows={true} ref={carouselRef}   afterChange={(newSlideIndex) => {
  setInternalSlide(newSlideIndex);
  if (onSlideChange) {
    onSlideChange(newSlideIndex + 1);
  }
}}
        >
          {imageChunks.map((chunk, index) => (
            <div key={index}>
              <Row gutter={[16, 16]}>
                {chunk.map((image: any, idx: number) => (
                  <Col key={idx} span={8}>
                    <div onClick={(e) => handleInfoClick(image, e)}>
                      <Card
                        hoverable
                        className="custom-card relative"
                        cover={
                          <div className="relative">
                            <img
                              alt={image.figtitle}
                              src={image.image_url}
                              className="w-full h-auto"
                            />
                            {/* Info Icon */}
                            <a
                              href={
                                image.pmcid
                                  ? `https://pmc.ncbi.nlm.nih.gov/articles/${image.pmcid}`
                                  : `https://pubmed.ncbi.nlm.nih.gov/${image.pmid}`
                              }
                              className="absolute top-2 right-2"
                              target="_blank"
                              onClick={(e) => e.stopPropagation()}
                              rel="noopener noreferrer"
                            >
                              <ExternalLinkIcon className=" text-blue-500 hover:text-blue-700 h-6 w-5"  />
                            </a>
                           
                          </div>
                        }
                      >
                        <Card.Meta
                          title={
                            <div
                              style={{
                                // display: "block",
                                whiteSpace: "normal",
                                maxHeight: "100px",
                                // lineClamp: 3,

                                textOverflow: "ellipsis",
                                display: "-webkit-box",
                                WebkitLineClamp: 3,
                                WebkitBoxOrient: "vertical",
                              }}
                            >
                              {/* <Tooltip title={image.figtitle}> */}
                              <span>{image.figtitle}</span>
                              {/* </Tooltip> */}
                            </div>
                          }
                        />
                      </Card>
                    </div>
                  </Col>
                ))}
              </Row>
            </div>
          ))}
        </Carousel>
      </ConfigProvider>

      {/* Modal */}
      <Modal
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        footer={null}
        title={
          <div className="flex justify-end mr-6 -mt-1 items-center ">
            <a
              href={
                selectedImage?.pmcid
                  ? `https://pmc.ncbi.nlm.nih.gov/articles/${selectedImage.pmcid}`
                  : selectedImage?.pmid
                  ? `https://pubmed.ncbi.nlm.nih.gov/${selectedImage.pmid}`
                  : "#"
              }
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
            >
              <ExternalLinkIcon className="text-blue-500 hover:text-blue-700 h-6 w-5" />
            </a>
          </div>
        }
        centered
        width={1400}
      >
        {selectedImage && (
          <Row gutter={24} align="top">
            {/* Left: Image */}
            <Col span={12}>
              <img
                src={selectedImage.image_url}
                alt={selectedImage.figtitle}
                className="w-full rounded-lg border max-h-[80vh] object-contain"
              />
            </Col>

            {/* Right: Content */}
            <Col span={10}>
              <div className="card-back-content">
                {selectedImage.figtitle &&
                  isPresent(selectedImage.figtitle) && (
                    <div className="pb-2 mb-2 border-b-2">
                      <h3 className="text-lg font-semibold mb-1">Caption:</h3>
                      <p className=" leading-tight text-base">
                        {selectedImage.figtitle}
                      </p>
                    </div>
                  )}
                {selectedImage.drugs && isPresent(selectedImage.drugs) && (
                  <div className="pb-2 mb-2 border-b-2">
                    <h3 className="text-lg font-semibold mb-1"> Drugs:</h3>
                    <p className=" leading-tight text-base">
                      {selectedImage.drugs}
                    </p>
                  </div>
                )}

                {selectedImage.process && isPresent(selectedImage.process) && (
                  <div className="pb-2 mb-2 border-b-2">
                    <h3 className="text-lg font-semibold mb-1"> Process:</h3>
                    <p className=" leading-tight text-base">
                      {selectedImage.process}
                    </p>
                  </div>
                )}

                {selectedImage.insights &&
                  isPresent(selectedImage.insights) && (
                    <div className="pb-2 mb-2 border-b-2">
                      <h3 className="text-lg font-semibold mb-1"> Insights:</h3>
                      <p className=" leading-tight text-base">
                        {selectedImage.insights}
                      </p>
                    </div>
                  )}
              </div>
            </Col>
          </Row>
        )}
      </Modal>
    </>
  );
};

export default CarouselComponent;
