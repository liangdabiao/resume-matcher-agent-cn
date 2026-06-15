import JobDescriptionUploadTextArea from '@/components/jd-upload/text-area';
import BackgroundContainer from '@/components/common/background-container';
import { Suspense } from 'react';

const ProvideJobDescriptionsPage = () => {
	return (
		<BackgroundContainer>
			<div className="flex flex-col items-center justify-center max-w-7xl">
				<h1 className="text-6xl font-bold text-center mb-12 text-white">
					粘贴岗位描述
				</h1>
				<p className="text-center text-gray-300 text-xl mb-8 max-w-xl mx-auto">
					请粘贴目标岗位 JD。系统会结合你的简历进行匹配分析，并生成修改建议。
					
				</p>
				<Suspense fallback={<div>正在加载输入框...</div>}>
					<JobDescriptionUploadTextArea />
				</Suspense>
			</div>
		</BackgroundContainer>
	);
};

export default ProvideJobDescriptionsPage;
