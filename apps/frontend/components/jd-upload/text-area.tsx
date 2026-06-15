'use client';

import React, { useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { useResumePreview } from '@/components/common/resume_previewer_context';
import { uploadJobDescriptions, improveResumeStream } from '@/lib/api/resume';

type SubmissionStatus = 'idle' | 'submitting' | 'success' | 'error';
type ImprovementStatus = 'idle' | 'improving' | 'error';

export default function JobDescriptionUploadTextArea() {
	const [text, setText] = useState('');
	const [flash, setFlash] = useState<{ type: 'error' | 'success'; message: string } | null>(null);
	const [submissionStatus, setSubmissionStatus] = useState<SubmissionStatus>('idle');
	const [improvementStatus, setImprovementStatus] = useState<ImprovementStatus>('idle');
	const [jobId, setJobId] = useState<string | null>(null);

	const { setImprovedData } = useResumePreview();
	const resumeId = useSearchParams().get('resume_id')!;
	const router = useRouter();

	const handleChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			setText(e.target.value);
			setFlash(null);
			if (submissionStatus !== 'idle') setSubmissionStatus('idle');
		},
		[submissionStatus]
	);

	const handleUpload = useCallback(
		async (e: React.FormEvent) => {
			e.preventDefault();
			const trimmed = text.trim();
			if (!trimmed) {
				setFlash({ type: 'error', message: '岗位描述不能为空。' });
				return;
			}
			if (!resumeId) {
				setFlash({ type: 'error', message: '缺少简历 ID，请重新上传简历。' });
				return;
			}

			setSubmissionStatus('submitting');
			try {
				const id = await uploadJobDescriptions([trimmed], resumeId);
				setJobId(id);
				setSubmissionStatus('success');
				setFlash({ type: 'success', message: '岗位描述提交成功！' });
			} catch (err) {
				console.error(err);
				setSubmissionStatus('error');
				setFlash({ type: 'error', message: (err as Error).message });
			}
		},
		[text, resumeId]
	);

	const [progressMessage, setProgressMessage] = useState<string>('');
	const handleImprove = useCallback(async () => {
		if (!jobId) return;

		setImprovementStatus('improving');
		setProgressMessage('准备开始...');
		try {
			const preview = await improveResumeStream(resumeId, jobId, (_status, message) => {
				setProgressMessage(message);
			});
			setImprovedData(preview);
			router.push('/dashboard');
		} catch (err) {
			console.error(err);
			setImprovementStatus('error');
			setFlash({ type: 'error', message: (err as Error).message });
		}
	}, [resumeId, jobId, setImprovedData, router]);

	const isNextDisabled = text.trim() === '' || submissionStatus === 'submitting';

	return (
		<form onSubmit={handleUpload} className="p-4 mx-auto w-full max-w-xl">
			{flash && (
				<div
					className={`p-3 mb-4 text-sm rounded-md ${flash.type === 'error'
						? 'bg-red-50 border border-red-200 text-red-800 dark:bg-red-900/20 dark:border-red-800/30 dark:text-red-300'
						: 'bg-green-50 border border-green-200 text-green-800 dark:bg-green-900/20 dark:border-green-800/30 dark:text-green-300'
						}`}
					role="alert"
				>
					<p>{flash.message}</p>
				</div>
			)}

			<div className="mb-6 relative">
				<label
					htmlFor="jobDescription"
					className="bg-zinc-950/80 text-white absolute start-1 top-0 z-10 block -translate-y-1/2 px-2 text-xs font-medium group-has-disabled:opacity-50"
				>
					岗位描述 <span className="text-red-500">*</span>
				</label>
				<Textarea
					id="jobDescription"
					rows={15}
					value={text}
					onChange={handleChange}
					required
					aria-required="true"
					placeholder="请粘贴岗位描述..."
					className="w-full bg-gray-800/30 focus:ring-1 border rounded-md dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500/50 border-gray-300 min-h-[300px]"
				/>
			</div>

			<div className="flex justify-end pt-4">
				<Button
					type="submit"
					disabled={isNextDisabled}
					aria-disabled={isNextDisabled}
					className={`font-semibold py-2 px-6 rounded flex items-center justify-center min-w-[90px] transition-all duration-200 ease-in-out ${isNextDisabled
						? 'bg-gray-400 dark:bg-gray-600 text-gray-600 dark:text-gray-400 cursor-not-allowed'
						: 'bg-blue-600 hover:bg-blue-700 text-white dark:bg-blue-500 dark:hover:bg-blue-600'
						}`}
				>
					{submissionStatus === 'submitting' ? (
						<>
							<svg
								className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
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
							<span>提交中...</span>
						</>
					) : submissionStatus === 'success' ? (
						<span>已提交</span>
					) : (
						<span>下一步</span>
					)}
				</Button>
			</div>

			{submissionStatus === 'success' && jobId && (
				<>
					<div className="flex justify-end mt-2">
						<Button
							onClick={handleImprove}
							disabled={improvementStatus === 'improving'}
							className="font-semibold py-2 px-6 rounded min-w-[90px] bg-green-600 hover:bg-green-700 text-white"
						>
							{improvementStatus === 'improving' ? '正在分析...' : '开始优化'}
						</Button>
					</div>
					{improvementStatus === 'improving' && progressMessage && (
						<div
							className="mt-3 p-3 text-sm rounded-md bg-blue-50 border border-blue-200 text-blue-800 dark:bg-blue-900/20 dark:border-blue-800/30 dark:text-blue-300 flex items-center"
							role="status"
							aria-live="polite"
						>
							<svg
								className="animate-spin -ml-1 mr-2 h-4 w-4"
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
							<span>{progressMessage}</span>
						</div>
					)}
				</>
			)}
		</form>
	);
}