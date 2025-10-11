import { useState, useEffect,useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Form, Select, ConfigProvider } from 'antd';
import type { FormProps } from 'antd';
import { capitalizeFirstLetter } from '../utils/helper';
import gifImage from "../assets/Merged-dossier (4).png";
import { useLocation } from 'react-router-dom';
import { parseQueryParams } from '../utils/parseUrlParams';
// import { SearchOutlined } from '@ant-design/icons';
// import { fetchData } from '../utils/fetchData';

type FieldType = {
  target?: string;
  indications?: string[];
  diseaseArea?: string[];
};

const targetOptions = ["SAV1", "CAMK2D", "DNM1L", "ENHO", "GUCY1B1", "GUCY1A1", "USP30", "SVEP1"]
const diseaseAreaOptions = [ "Cardiovascular diseases", "Urologic diseases"]
const indicationOptions = ["Obesity"]
const { Option } = Select;
const diseaseToTargetMap: Record<string, string[]> = {
  "Cardiovascular diseases": ["CAMK2D","DNM1L","ENHO","GUCY1A1","SAV1",],
  "Urologic diseases": ["CAMK2D","GUCY1A1"],
};

const indicationToTargetMap: Record<string, string[]> = {
  "Obesity": []
};
const HomeLocked = ({ setAppState }) => {

  const targetToIndicationMap = useMemo(() => {
    const map = {};
    for (const indication in indicationToTargetMap) {
      const targets = indicationToTargetMap[indication];
      for (const t of targets) {
        if (!map[t]) {
          map[t] = [];
        }
        map[t].push(indication);
      }
    }
    return map;
  }, [indicationToTargetMap]);

  const targetToDiseaseAreaMap = useMemo(() => {
    const map = {};
    for (const diseaseArea in diseaseToTargetMap) {
      const targets = diseaseToTargetMap[diseaseArea];
      for (const t of targets) {
        if (!map[t]) {
          map[t] = [];
        }
        map[t].push(diseaseArea);
      }
    }
    return map;
  }, [diseaseToTargetMap]);

  const navigate = useNavigate();
  const location = useLocation();

  const [target, setTarget] = useState('');
  const [form] = Form.useForm();
  const indicationsValue = Form.useWatch('indications', form);
  const diseaseAreaValue = Form.useWatch('diseaseArea', form);
  const targetValue = Form.useWatch('target', form);

  const [validTargets, setValidTargets] = useState(new Set(targetOptions));
  const [validDiseaseAreas, setValidDiseaseAreas] = useState(new Set(diseaseAreaOptions));
  const [validIndications, setValidIndications] = useState(new Set(indicationOptions));

  useEffect(() => {
    const queryParams = new URLSearchParams(location.search);
    const { target, indications,diseaseArea } = parseQueryParams(queryParams);

    const parsedIndications = indications ? indications.map((indication) => capitalizeFirstLetter(indication)) : [];
    const parsedDiseaseAreas = diseaseArea ? diseaseArea.map((area) => capitalizeFirstLetter(area)) : [];
    

    setTarget(target);
    form.setFieldsValue({ target: target, indications: parsedIndications,diseaseArea:parsedDiseaseAreas });
  }, [location, form]);

  useEffect(() => {
    let vt = new Set(targetOptions);
    let vd = new Set(diseaseAreaOptions);
    let vi = new Set(indicationOptions);

    if (targetValue) {
        vd = new Set(targetToDiseaseAreaMap[targetValue] || []);
        vi = new Set(targetToIndicationMap[targetValue] || []);
    } else if (diseaseAreaValue && diseaseAreaValue.length > 0) {
        const relatedTargets = new Set<string>();
        diseaseAreaValue.forEach(da => {
            (diseaseToTargetMap[da] || []).forEach(t => relatedTargets.add(t));
        });
        vt = relatedTargets;
    } else if (indicationsValue && indicationsValue.length > 0) {
        const relatedTargets = new Set<string>();
        indicationsValue.forEach(i => {
            (indicationToTargetMap[i] || []).forEach(t => relatedTargets.add(t));
        });
        vt = relatedTargets;
    }

    setValidTargets(vt);
    setValidDiseaseAreas(vd);
    setValidIndications(vi);

    if (targetValue && !vt.has(targetValue)) {
        form.setFieldsValue({ target: null });
    }
    if (diseaseAreaValue && diseaseAreaValue.some(da => !vd.has(da))) {
        form.setFieldsValue({ diseaseArea: [] });
    }
    if (indicationsValue && indicationsValue.some(i => !vi.has(i))) {
        form.setFieldsValue({ indications: [] });
    }

    if (diseaseAreaValue && diseaseAreaValue.length > 0) {
        form.setFieldsValue({ indications: [] });
    } else if (indicationsValue && indicationsValue.length > 0) {
        form.setFieldsValue({ diseaseArea: [] });
    }
  }, [targetValue, diseaseAreaValue, indicationsValue, form, targetToDiseaseAreaMap, targetToIndicationMap]);


  // const handleSearch = (value) => {
  //   if (value) {
  //     fetchSuggestions(value);
  //   } else {
  //     setOptions([]);
  //   }
  // };


  const onFinish: FormProps<FieldType>['onFinish'] = (values) => {
  

    const encodedIndications = values.indications
      .map((indication) => `"${capitalizeFirstLetter(indication)}"`)
      .join(',');
      const encodedDiseaseArea = values.diseaseArea
      .map((disease) => `"${capitalizeFirstLetter(disease)}"`)
      .join(',');
      
        
      
    setAppState((prev) => ({
      ...prev,
      target: values.target,
      indications: values.indications || [],
      diseaseArea: values.diseaseArea || [],
    }));
    navigate(`/target-biology?target=${values.target}&indications=${encodeURIComponent(encodedIndications)}&diseaseArea=${encodeURIComponent(encodedDiseaseArea)}`);
  };
  const handleTargetChange = (value) => {
    setTarget(value);
  }

  const isButtonEnabled = target && ((indicationsValue && indicationsValue.length > 0) || (diseaseAreaValue && diseaseAreaValue.length > 0));
  return (
    <>
      <div className="bg-gradient-to-b h-[86vh] from-indigo-50 to-white hero">
        <div className="max-w-[96rem] mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center mb-8">
            <h3 className="text-4xl text-gray-900 font-bold mb-4">
              Disease Biomarker & Target Insights Platform & Services (DBTIPS™)
            </h3>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Your guide to transforming complex data into actionable insights and empower target validation, and advancing precision-driven research and innovation.</p>        </div>
          <section className="grid grid-cols-1 md:grid-cols-2 gap-12  ">
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
                  {/* <Form.Item
                  label="Target:"
                  name="target"
                  rules={[{ message: "Please input your target!" }]}

                >
                  <Input
                    placeholder="Please enter a target!"
                    prefix={<SearchOutlined className="text-2xl" />}
                    className="w-full pl-4 pr-4 py-4 rounded-xl border-2 border-gray-100 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all text-lg"
                    onChange={handleTargetChange}
                  />
                </Form.Item> */}
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
                    <Form.Item name="target" label="Target:">

                      <Select
                        showSearch={true}
                        size="large"
                        placeholder="Please select a target"
                        className=" rounded-xl border-2 border-gray-100 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all text-lg "
                        allowClear
                        onChange={handleTargetChange}
                      
                      >
                        {targetOptions.map((option) => (
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
                      disabled={indicationsValue && indicationsValue.length > 0}
                      placeholder="Please select an disease area(s)"
                      className=" rounded-xl border-2 border-gray-100 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all text-lg "
                      allowClear
                    >
                      {diseaseAreaOptions.map((option) => (
                        <Option key={option} value={capitalizeFirstLetter(option)} disabled={!validDiseaseAreas.has(option)}>
                          {capitalizeFirstLetter(option)}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                    <Form.Item name="indications" label="Disease:">

                      <Select
                        mode="multiple"
                        showSearch={true}
                        size="large"
                        disabled={diseaseAreaValue && diseaseAreaValue.length > 0}
                        placeholder="Please select an indication(s)"
                        className=" rounded-xl border-2 border-gray-100 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 outline-none transition-all text-lg "
                        allowClear
                        
                      >
                        {indicationOptions.map((option) => (
                          <Option key={option} value={capitalizeFirstLetter(option)} disabled={!validIndications.has(option)}>
                            {capitalizeFirstLetter(option)}
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

    </>
  );
};

export default HomeLocked;