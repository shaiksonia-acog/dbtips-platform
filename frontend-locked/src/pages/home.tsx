import {  useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Form, Select, ConfigProvider } from 'antd';
import type { FormProps } from 'antd';
import { capitalizeFirstLetter } from '../utils/helper';
import gifImage from "../assets/Merged-dossier (4).png";
import { useLocation } from 'react-router-dom';
import { parseQueryParams } from '../utils/parseUrlParams';

type FieldType = {
  target?: string;
  indications?: string[];
  diseaseArea?: string[];
};

const targetOptions = ["ACVR2A","ACVR2B","ANO4","ANGPTL7","APLNR","BRINP2","CAMK2D", "CRHR2","DNM1L", "ENHO","GPR75","HTRA1","INHBE","GIPR", "GUCY1A1","GUCY1B1", "MIR33A","PDE3B","SAV1","SVEP1","USP19","USP30"]
const diseaseAreaOptions = [ "Cardiovascular diseases", "Urologic diseases"]
const indicationOptions = ["Age-related macular degeneration","Glaucoma","Obesity"]
const { Option } = Select;

const diseaseToTargetMap: Record<string, string[]> = {
  "Cardiovascular diseases": ["CAMK2D","DNM1L","ENHO","GUCY1A1","GUCY1B1","SAV1","SVEP1","USP30"],
  "Urologic diseases": ["CAMK2D","GUCY1A1","GUCY1B1"],
};

const indicationToTargetMap: Record<string, string[]> = {
  "Obesity": ["ACVR2A","ACVR2B","ANO4","APLNR","BRINP2","CRHR2","GIPR","GPR75","INHBE","MIR33A","PDE3B","USP19"],
  "Age-related macular degeneration": ["HTRA1"],
  "Glaucoma": ["ANGPTL7"],

};

const HomeLocked = ({ setAppState }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [form] = Form.useForm();
  
  const indicationsValue = Form.useWatch('indications', form);
  const diseaseAreaValue = Form.useWatch('diseaseArea', form);
  const targetValue = Form.useWatch('target', form);

  // Create reverse maps (target -> indications/diseaseAreas)
  const targetToIndicationMap = useMemo(() => {
    const map: Record<string, string[]> = {};
    Object.entries(indicationToTargetMap).forEach(([indication, targets]) => {
      targets.forEach(t => {
        if (!map[t]) map[t] = [];
        map[t].push(indication);
      });
    });
    return map;
  }, []);

  const targetToDiseaseAreaMap = useMemo(() => {
    const map: Record<string, string[]> = {};
    Object.entries(diseaseToTargetMap).forEach(([diseaseArea, targets]) => {
      targets.forEach(t => {
        if (!map[t]) map[t] = [];
        map[t].push(diseaseArea);
      });
    });
    return map;
  }, []);

  // Calculate valid options based on current selections
  const { validTargets, validDiseaseAreas, validIndications } = useMemo(() => {
    let vt = new Set(targetOptions);
    let vd = new Set(diseaseAreaOptions);
    let vi = new Set(indicationOptions);

    const targetFromDisease = diseaseAreaValue?.length > 0;
    const targetFromIndication = indicationsValue?.length > 0;

    if (targetFromDisease) {
      const relatedTargets = new Set<string>();
      diseaseAreaValue.forEach(da => {
        (diseaseToTargetMap[da] || []).forEach(t => relatedTargets.add(t));
      });
      vt = relatedTargets;
    } else if (targetFromIndication) {
      const relatedTargets = new Set<string>();
      indicationsValue.forEach(i => {
        (indicationToTargetMap[i] || []).forEach(t => relatedTargets.add(t));
      });
      vt = relatedTargets;
    }

    if (targetValue) {
      const relatedDiseaseAreas = new Set(targetToDiseaseAreaMap[targetValue] || []);
      const relatedIndications = new Set(targetToIndicationMap[targetValue] || []);
      if (targetFromDisease) {
        vd = new Set([...vd].filter(x => relatedDiseaseAreas.has(x)));
      } else {
        vd = relatedDiseaseAreas;
      }
      if (targetFromIndication) {
        vi = new Set([...vi].filter(x => relatedIndications.has(x)));
      } else {
        vi = relatedIndications;
      }
    }

    return { validTargets: vt, validDiseaseAreas: vd, validIndications: vi };
  }, [targetValue, diseaseAreaValue, indicationsValue, targetToDiseaseAreaMap, targetToIndicationMap]);

  // Initialize form from URL params
  useEffect(() => {
    const queryParams = new URLSearchParams(location.search);
    const { target, indications, diseaseArea } = parseQueryParams(queryParams);

    const parsedIndications = indications?.map(i => capitalizeFirstLetter(i)) || [];
    const parsedDiseaseAreas = diseaseArea?.map(d => capitalizeFirstLetter(d)) || [];
    
    form.setFieldsValue({ 
      target, 
      indications: parsedIndications,
      diseaseArea: parsedDiseaseAreas 
    });
  }, [location, form]);

  // Clear invalid selections when filters change
  useEffect(() => {
    const currentValues = form.getFieldsValue();
    
    if (currentValues.target && !validTargets.has(currentValues.target)) {
      form.setFieldValue('target', null);
    }
    if (currentValues.diseaseArea?.some(da => !validDiseaseAreas.has(da))) {
      form.setFieldValue('diseaseArea', []);
    }
    if (currentValues.indications?.some(i => !validIndications.has(i))) {
      form.setFieldValue('indications', []);
    }
  }, [validTargets, validDiseaseAreas, validIndications, form]);

  // Mutual exclusion: clear one when the other is selected
  const handleDiseaseAreaChange = (value: string[]) => {
    if (value?.length > 0) {
      form.setFieldValue('indications', []);
    }
  };

  const handleIndicationsChange = (value: string[]) => {
    if (value?.length > 0) {
      form.setFieldValue('diseaseArea', []);
    }
  };

  const onFinish: FormProps<FieldType>['onFinish'] = (values) => {
    const encodedIndications = values.indications
      ?.map(i => `"${capitalizeFirstLetter(i)}"`)
      .join(',') || '';
    const encodedDiseaseArea = values.diseaseArea
      ?.map(d => `"${capitalizeFirstLetter(d)}"`)
      .join(',') || '';
      
    setAppState((prev) => ({
      ...prev,
      target: values.target,
      indications: values.indications || [],
      diseaseArea: values.diseaseArea || [],
    }));
    
    navigate(`/target-biology?target=${values.target}&indications=${encodeURIComponent(encodedIndications)}&diseaseArea=${encodeURIComponent(encodedDiseaseArea)}`);
  };

  const isButtonEnabled = targetValue;

  return (
    <div className="bg-gradient-to-b h-[86vh] from-indigo-50 to-white hero">
      <div className="max-w-[96rem] mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center mb-8">
          <h3 className="text-4xl text-gray-900 font-bold mb-4">
            Disease Biomarker & Target Insights Platform & Services (DBTIPS™)
          </h3>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Your guide to transforming complex data into actionable insights and empower target validation, and advancing precision-driven research and innovation.
          </p>
        </div>
        
        <section className="grid grid-cols-1 md:grid-cols-2 gap-12">
          <div>
            <img
              src={gifImage}
              alt="Informative GIF"
              className="w-full h-[60vh] object-contain rounded-lg"
              loading='lazy'
            />
          </div>
          
          <div className='flex items-center'>
            <div className='w-full'>
              <Form
                form={form}
                layout="vertical"
                labelWrap={true}
                className="max-w-2xl mx-auto mb-16"
                style={{ width: '100%' }}
                onFinish={onFinish}
              >
                <ConfigProvider
                  theme={{
                    components: {
                      Select: {
                        multipleItemHeightLG: 38,
                      },
                    },
                    token: {
                      controlHeight: 44,
                      paddingSM: 17,
                    },
                  }}
                >
                  <Form.Item name="target" label="Target:" rules={[{ required: true }]}>
                    <Select
                      showSearch={true}
                      size="large"
                      placeholder="Please select a target"
                      className="rounded-xl border-2 border-gray-100 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all text-lg"
                      allowClear
                    >
                      {targetOptions.map(option => (
                        <Option key={option} value={option} disabled={!validTargets.has(option)}>
                          {option}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>

                  <Form.Item name="diseaseArea" label="Disease Area:">
                    <Select
                      mode="multiple"
                      showSearch={true}
                      size="large"
                      disabled={
                        (indicationsValue?.length > 0) || 
                        (targetValue && validDiseaseAreas.size === 0)
                      }
                      placeholder="Please select disease area(s)"
                      className="rounded-xl border-2 border-gray-100 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all text-lg"
                      allowClear
                      onChange={handleDiseaseAreaChange}
                    >
                      {diseaseAreaOptions.map(option => (
                        <Option key={option} value={option} disabled={!validDiseaseAreas.has(option)}>
                          {option}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>

                  <Form.Item name="indications" label="Disease:">
                    <Select
                      mode="multiple"
                      showSearch={true}
                    placement='topLeft'
                      size="large"
                      disabled={
                        (diseaseAreaValue?.length > 0) || 
                        (targetValue && validIndications.size === 0)
                      }
                      placeholder="Please select disease(s)"
                      className="rounded-xl border-2 border-gray-100 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all text-lg"
                      allowClear
                      onChange={handleIndicationsChange}
                    >
                      {indicationOptions.map(option => (
                        <Option key={option} value={option} disabled={!validIndications.has(option)}>
                          {option}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </ConfigProvider>

                <Form.Item>
                  <Button
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white py-6 px-6 rounded-xl font-semibold text-lg transition-all duration-200 flex items-center justify-center gap-2 hover:gap-3"
                    htmlType="submit"
                    disabled={!isButtonEnabled}
                  >
                    Search
                  </Button>
                </Form.Item>
              </Form>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default HomeLocked;
