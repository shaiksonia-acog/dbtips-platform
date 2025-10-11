import { useEffect, useRef, useCallback, useState } from 'react';
import parse from "html-react-parser";

const CustomTooltip = ({ content, x, y , title }: { content: React.ReactNode; x: number; y: number, title:string }) => (
  <div
    className="absolute z-[9999999999999] max-w-sm bg-black text-white  rounded shadow-lg"
    style={{
      top: y,
      left: x,
      // pointerEvents: 'none'
    }}
  >
    {/* Arrow */}
    <div 
      className="absolute w-3 h-3 bg-black  rotate-45"
      style={{
        top: -6,
        left: 20,
        borderColor: 'inherit'
      }}
    />
    
    {/* Content */}
    <div className="relative p-2 text-sm">
      <div className='mb-2 text-lg'>
        {parse(title)}
      </div>
      <div className="content">
        {content}
      </div>
    </div>
  </div>
);

const ProteinStructure = ({ uniprot_id }: { uniprot_id: string }) => {
  const protvistaUniprotRef = useRef<HTMLElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltipData, setTooltipData] = useState<{
    visible: boolean;
    content: React.ReactNode;
    x: number;
    y: number;
    title: string;
  }>({
    visible: false,
    content: '',
    x: 0,
    y: 0,
    title: ''
  });

  const onProtvistaEvent = useCallback((e: Event) => {
    const { detail } = e as CustomEvent;
    
    if (detail?.eventType === 'click') {
      const mouseEvent = detail?.parentEvent;
      const feature = detail?.feature;
      // Get the relative position within the container
      const containerRect = containerRef.current?.getBoundingClientRect();
      const relativeY = mouseEvent.clientY - (containerRect?.top || 0);
      const relativeX = mouseEvent.clientX - (containerRect?.left || 0);
      const title =
      feature.type && feature.start && feature.end
        ? `<h4>${feature.type} ${feature.start}-${feature.end}</h4><hr />`
        : '';
      setTooltipData({
        visible: true,
        content: parse(detail?.feature?.tooltipContent || 'No content available'),
        x: relativeX -22 || 0,
        y: relativeY,
        title
      });
    }
  }, []);

  useEffect(() => {
    const ref = protvistaUniprotRef.current;
    if (ref) {
      ref.addEventListener('click', onProtvistaEvent);
      ref.addEventListener('change', onProtvistaEvent);
      ref.addEventListener('protvista-event', onProtvistaEvent);
    }

    return () => {
      if (ref) {
        ref.removeEventListener('click', onProtvistaEvent);
        ref.removeEventListener('change', onProtvistaEvent);
        ref.removeEventListener('protvista-event', onProtvistaEvent);
      }
    };
  }, [onProtvistaEvent]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const ref = protvistaUniprotRef.current;
      if (ref && !ref.contains(e.target as Node)) {
        setTooltipData(prev => ({
          ...prev,
          visible: false
        }));
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  return (
    <section id="protein-structure" className="mt-12 px-[5vw]">
      <h1 className="text-3xl font-semibold">
        Protein structure, sequence, domain organization and mutation(s)
      </h1>
      <p className="mt-2  font-medium">
        Protein structural information serves as the cornerstone for
        comprehending a target protein's behavior, interactions, and therapeutic
        potential in drug development.
      </p>

      <div className="mt-4 relative" ref={containerRef}>
        {/* @ts-expect-error */}
        <protvista-uniprot
          ref={protvistaUniprotRef}
          accession={uniprot_id}
        />
        
        {tooltipData.visible && tooltipData.content && (
          <CustomTooltip
            content={tooltipData.content}
            x={tooltipData.x}
            y={tooltipData.y}
            title={tooltipData.title}
          />
        )}
      </div>
    </section>
  );
};

export default ProteinStructure;