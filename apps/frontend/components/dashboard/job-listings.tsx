import React, { useState, useEffect } from 'react';
import PasteJobDescription from './paste-job-description';
import { uploadJobDescriptions, getJob } from '@/lib/api/job';
import { improveResumeStream } from '@/lib/api/resume';
import { useResumePreview } from '@/components/common/resume_previewer_context';

interface Job {
	id?: number;
	title: string;
	company: string;
	location: string;
	jobId: string;
	requirements: string[];
	responsibilities: string[];
}

type AnalyzedJobData = Pick<Job, 'title' | 'company' | 'location' | 'jobId' | 'requirements' | 'responsibilities'> & {
	job_summary?: string;
	key_responsibilities?: string[];
};

interface JobListingsProps {
	resumeId: string;
}

const JobListings: React.FC<JobListingsProps> = ({ resumeId }) => {
	const { improvedData, setImprovedData } = useResumePreview();
	const [isModalOpen, setIsModalOpen] = useState(false);
	const [analyzedJob, setAnalyzedJob] = useState<AnalyzedJobData | null>(null);
	const [isAnalyzing, setIsAnalyzing] = useState(false);
	const [isImproving, setIsImproving] = useState(false);
	const [loadingInitialJob, setLoadingInitialJob] = useState(true);
	// Optional: add error state for analysis failures
	// const [error, setError] = useState<string | null>(null);

	// Load initial job data when component mounts
	useEffect(() => {
		const loadInitialJob = async () => {
			if (improvedData?.data?.job_id) {
				try {
					setLoadingInitialJob(true);
						const jobData = await getJob(improvedData.data.job_id);
					
						const initialJobData: AnalyzedJobData = {
						title: jobData.processed_job?.job_title || '未知岗位',
						company: jobData.processed_job?.company_profile?.company_name || '未知公司',
						location: jobData.processed_job?.location?.city || '未知地点',
						requirements: jobData.processed_job?.job_requirements?.split('\n').filter(Boolean) || [],
						responsibilities: jobData.processed_job?.job_responsibilities?.split('\n').filter(Boolean) || [],
						job_summary: jobData.processed_job?.job_summary || '',
						key_responsibilities: jobData.processed_job?.key_responsibilities || [],
						jobId: improvedData.data.job_id
					};
					
					setAnalyzedJob(initialJobData);
				} catch (err) {
					console.error('Error loading initial job:', err);
				} finally {
					setLoadingInitialJob(false);
				}
			} else {
				setLoadingInitialJob(false);
			}
		};
		
		loadInitialJob();
	}, [improvedData]);

	const handleOpenModal = () => {
		// setError(null); // Clear previous errors when opening modal
		setIsModalOpen(true);
	};
	const handleCloseModal = () => setIsModalOpen(false);

	const handlePasteAndAnalyzeJob = async (text: string) => {
		setIsAnalyzing(true);
		setAnalyzedJob(null); // Clear previous job
		// setError(null); // Clear previous errors
		try {
			// Upload the job description
			const jobId = await uploadJobDescriptions([text], resumeId);
			
			// Get the processed job data
			const jobData = await getJob(jobId);
			
			// Extract relevant information from the processed job
			const analyzedData: AnalyzedJobData = {
				title: jobData.processed_job?.job_title || '未知岗位',
				company: jobData.processed_job?.company_profile?.company_name || '未知公司',
				location: jobData.processed_job?.location?.city || '未知地点',
				requirements: jobData.processed_job?.job_requirements?.split('\n').filter(Boolean) || [],
				responsibilities: jobData.processed_job?.job_responsibilities?.split('\n').filter(Boolean) || [],
				job_summary: jobData.processed_job?.job_summary || '',
				key_responsibilities: jobData.processed_job?.key_responsibilities || [],
				jobId: jobId
			};
			
			setAnalyzedJob(analyzedData);
		} catch (err) {
			console.error('Error analyzing job description:', err);
			// setError(err instanceof Error ? err.message : "An unknown error occurred during analysis.");
			setAnalyzedJob(null);
		} finally {
			setIsAnalyzing(false);
			handleCloseModal();
		}
	};

	const handleImproveResume = async () => {
		console.log('handleImproveResume called');
		console.log('analyzedJob:', analyzedJob);
		console.log('resumeId:', resumeId);
		
		if (!analyzedJob) {
			console.log('No analyzed job, returning');
			return;
		}
		
		setIsImproving(true);
		setImproveProgress('准备开始...');
		try {
			console.log('Calling improveResumeStream with resumeId:', resumeId, 'and jobId:', analyzedJob.jobId);
			// Call the streaming improveResume API
			const improvedResult = await improveResumeStream(
				resumeId,
				analyzedJob.jobId,
				(_status, message) => setImproveProgress(message)
			);
			console.log('improveResumeStream response:', improvedResult);
			// Update the resume preview context with the improved data
			setImprovedData(improvedResult);
			// Show a success message
			alert('简历已成功优化！');
		} catch (err) {
			console.error('Error improving resume:', err);
			alert('简历优化失败，请稍后重试。');
		} finally {
			setIsImproving(false);
			setImproveProgress('');
		}
	};

	// truncateText function removed as it's no longer used

	return (
		<div className="bg-gray-900/80 backdrop-blur-sm p-6 rounded-lg shadow-xl border border-gray-800/50">
			<h2 className="text-2xl font-bold text-white mb-1">岗位分析</h2>
			<p className="text-gray-400 mb-6 text-sm">
				{analyzedJob
					? '岗位解析结果如下。'
					: '上传岗位描述后，系统会提取关键要求。'}
			</p>
			{loadingInitialJob ? (
				<div className="text-center text-gray-400 py-8">
					<p>正在加载岗位详情...</p>
				</div>
			) : isAnalyzing ? (
				<div className="text-center text-gray-400 py-8">
					<p>正在分析岗位描述...</p>
				</div>
			) : analyzedJob ? (
				<div className="space-y-4">
					<div
						// key is not needed for a single item display
						className="p-4 bg-gray-700 rounded-md shadow-md"
					>
						<h3 className="text-lg font-semibold text-gray-100">{analyzedJob.title}</h3>
						<p className="text-sm text-gray-300">{analyzedJob.company}</p>
						<p className="text-xs text-gray-400 mt-1">{analyzedJob.location}</p>
						
						{/* 岗位概述 */}
						{analyzedJob.job_summary && (
							<div className="mt-3">
								<h4 className="text-sm font-medium text-gray-200 mb-1">岗位概述</h4>
								<p className="text-xs text-gray-400">{analyzedJob.job_summary}</p>
							</div>
						)}
						
						{analyzedJob.requirements && analyzedJob.requirements.length > 0 && (
							<div className="mt-3">
								<h4 className="text-sm font-medium text-gray-200 mb-1">岗位要求</h4>
								<ul className="text-xs text-gray-400 list-disc list-inside space-y-1">
									{analyzedJob.requirements.slice(0, 3).map((req, index) => (
										<li key={index}>{req}</li>
									))}
									{analyzedJob.requirements.length > 3 && (
										<li className="italic">还有 {analyzedJob.requirements.length - 3} 条要求</li>
									)}
								</ul>
							</div>
						)}
						
						{/* 核心职责 */}
						{(analyzedJob.key_responsibilities && analyzedJob.key_responsibilities.length > 0) ? (
							<div className="mt-3">
								<h4 className="text-sm font-medium text-gray-200 mb-1">核心职责</h4>
								<ul className="text-xs text-gray-400 list-disc list-inside space-y-1">
									{analyzedJob.key_responsibilities.slice(0, 5).map((resp, index) => (
										<li key={index}>{resp}</li>
									))}
									{analyzedJob.key_responsibilities.length > 5 && (
										<li className="italic">还有 {analyzedJob.key_responsibilities.length - 5} 条职责</li>
									)}
								</ul>
							</div>
						) : (
							<div className="mt-3">
								<h4 className="text-sm font-medium text-gray-200 mb-1">核心职责</h4>
								<p className="text-xs text-gray-400">暂未提取到核心职责。</p>
							</div>
						)}
					</div>
					<div className="space-y-3 mt-4">
							<button
								onClick={handleOpenModal}
								className="w-full text-center block bg-green-600 hover:bg-green-700 text-white font-medium py-2.5 px-4 rounded-md transition-colors duration-200 text-sm"
							>
								分析另一个岗位
							</button>
							{isImproving ? (
							<div className="w-full text-center py-2.5 px-4 rounded-md bg-purple-900/30 text-purple-200 text-sm">
								<div className="flex items-center justify-center gap-2">
									<svg
										className="animate-spin h-4 w-4"
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										aria-hidden="true"
									>
										<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
										<path
											className="opacity-75"
											fill="currentColor"
											d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
										/>
									</svg>
									<span>{improveProgress || '正在优化简历...'}</span>
								</div>
							</div>
						) : (
							<button
								onClick={handleImproveResume}
								className="w-full text-center block bg-purple-600 hover:bg-purple-700 text-white font-medium py-2.5 px-4 rounded-md transition-colors duration-200 text-sm"
							>
								优化简历
							</button>
						)}
						</div>
				</div>
			) : (
				<div className="text-center text-gray-400 py-8 flex flex-col justify-center items-center">
					<p className="mb-3">暂未分析岗位描述。</p>
					<button
						onClick={handleOpenModal}
						className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors duration-200 text-sm"
					>
						上传岗位描述
					</button>
				</div>
			)}
			{isModalOpen && (
				<PasteJobDescription
					onClose={handleCloseModal}
					onPaste={handlePasteAndAnalyzeJob}
				/>
			)}
		</div>
	);
};

export default JobListings;
