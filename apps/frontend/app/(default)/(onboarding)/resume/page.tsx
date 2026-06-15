'use client';

import BackgroundContainer from '@/components/common/background-container';
import FileUpload from '@/components/common/file-upload';

export default function UploadResume() {
	return (
		<BackgroundContainer innerClassName="justify-start pt-16">
			<div className="w-full max-w-md mx-auto flex flex-col items-center gap-6">
				<h1 className="text-4xl font-bold text-center text-white mb-6">
					上传你的简历
				</h1>
				<p className="text-center text-gray-300 mb-8">
					将简历文件拖到下方，或点击选择文件。支持 PDF、DOCX，最大 2 MB。
					
				</p>
				<div className="w-full">
					<FileUpload />
				</div>
			</div>
		</BackgroundContainer>
	);
}
