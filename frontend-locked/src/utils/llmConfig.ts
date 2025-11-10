export const config = {
	widgetConfig: [
		{
			id: 'rnaseq',
			label: 'Rnaseq Data',
			description_prompt: '{$data}\n',
		},
		{
			id: 'pipeline_indications',
			label: 'Therapeutic pipeline',
			description_prompt: '{$data}',
		},
		{
			id: 'animal_models',
			label: 'Animal Models',
			description_prompt: '{$data}',
		},
		{
			id: 'literature',
			label: 'Literature',
			description_prompt: '{$data}',
		},
		{
			id: 'target_literature',
			label: 'Literature',
			description_prompt: '{$data}',
		},
		{
			id: 'pipeline_target',
			label: 'Therapeutic pipeline',
			description_prompt: '{$data}',
		},
		// {
		// 	id:"gwas",
		// 	label:"GWAS Studies",
		// 	description_prompt: '{$data}',
		// },
		{
			id:"patient_stories",
			label:"Patient Stories",
			description_prompt: '{$data}',
		},
	],
};
