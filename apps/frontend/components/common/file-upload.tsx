'use client';

import React, { useState } from 'react';
import {
	AlertCircleIcon,
	CheckCircle2Icon,
	Loader2Icon,
	PaperclipIcon,
	UploadIcon,
	XIcon,
} from 'lucide-react';
// Ensure FileMetadata is imported if you cast to it, or rely on structural typing.
// For this refinement, direct property access after casting to FileMetadata is used.
import { formatBytes, useFileUpload, FileMetadata } from '@/hooks/use-file-upload';
import { Button } from '@/components/ui/button';
import { API_URL } from '@/lib/api/config';

const acceptedFileTypes = [
	'application/pdf', // .pdf
	'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
];

const acceptString = acceptedFileTypes.join(',');
const API_RESUME_UPLOAD_URL = `${API_URL}/api/v1/resumes/upload`;

export default function FileUpload() {
	const maxSize = 2 * 1024 * 1024; // 2MB

	const [uploadFeedback, setUploadFeedback] = useState<{
		type: 'success' | 'error';
		message: string;
	} | null>(null);

	const [
		{ files, isDragging, errors: validationOrUploadErrors, isUploadingGlobal },
		{
			handleDragEnter,
			handleDragLeave,
			handleDragOver,
			handleDrop,
			openFileDialog,
			removeFile,
			getInputProps,
			clearErrors,
		},
	] = useFileUpload({
		maxSize,
		accept: acceptString,
		multiple: false,
		uploadUrl: API_RESUME_UPLOAD_URL,
		onUploadSuccess: (uploadedFile, response) => {
			console.log('Upload successful:', uploadedFile, response);
			// uploadedFile.file is FileMetadata here, as transformed by the hook
			const data = response as Record<string, unknown> & { resume_id?: string }
			const resumeId =
				typeof data.resume_id === 'string' ? data.resume_id : undefined

			if (!resumeId) {
				console.error('Missing resume_id in upload response', response)
				setUploadFeedback({
					type: 'error',
					message: '上传成功，但后端没有返回简历 ID。',
				})
				return
			}

			setUploadFeedback({
				type: 'success',
				message: `${(uploadedFile.file as FileMetadata).name} 上传成功！`,
			});
			clearErrors();
			const encodedResumeId = encodeURIComponent(resumeId);
			window.location.href = `/jobs?resume_id=${encodedResumeId}`;
		},
		onUploadError: (file, errorMsg) => {
			console.error('Upload error:', file, errorMsg);
			setUploadFeedback({
				type: 'error',
				message: errorMsg || '上传过程中发生未知错误。',
			});
		},
		onFilesChange: (currentFiles) => {
			if (currentFiles.length === 0) {
				setUploadFeedback(null);
			}
		},
	});

	const currentFile = files[0];

	const handleRemoveFile = (id: string) => {
		removeFile(id);
		setUploadFeedback(null);
	};

	const displayErrors =
		uploadFeedback?.type === 'error' ? [uploadFeedback.message] : validationOrUploadErrors;

	return (
		<div className="flex w-full flex-col gap-4 rounded-lg">
			<div
				role="button"
				tabIndex={!currentFile && !isUploadingGlobal ? 0 : -1}
				onClick={!currentFile && !isUploadingGlobal ? openFileDialog : undefined}
				onKeyDown={(e) => {
					if ((e.key === 'Enter' || e.key === ' ') && !currentFile && !isUploadingGlobal)
						openFileDialog();
				}}
				onDragEnter={!isUploadingGlobal ? handleDragEnter : undefined}
				onDragLeave={!isUploadingGlobal ? handleDragLeave : undefined}
				onDragOver={!isUploadingGlobal ? handleDragOver : undefined}
				onDrop={!isUploadingGlobal ? handleDrop : undefined}
				data-dragging={isDragging || undefined}
				className={`relative rounded-xl border-2 border-dashed transition-all duration-300 ease-in-out
                    ${currentFile || isUploadingGlobal
						? 'cursor-not-allowed opacity-70 border-gray-700'
						: 'cursor-pointer border-gray-600 hover:border-primary hover:bg-gray-900/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background'
					}
                    ${isDragging && !isUploadingGlobal
						? 'border-primary bg-primary/10'
						: 'bg-gray-900/50'
					}`}
				aria-disabled={Boolean(currentFile) || isUploadingGlobal}
				aria-label={
					currentFile
						? '已选择文件。移除后可重新上传。'
						: '简历上传区域。拖拽文件到此处，或点击选择文件。'
				}
			>
				<div className="flex min-h-48 w-full flex-col items-center justify-center p-6 text-center">
					<input {...getInputProps()} />
					{isUploadingGlobal ? (
						<>
							<Loader2Icon className="mb-4 size-10 animate-spin text-primary" />
							<p className="text-lg font-semibold text-white">上传中...</p>
							<p className="text-sm text-muted-foreground">
								正在解析并处理你的简历。
							</p>
						</>
					) : (
						<>
							<div className="mb-4 flex size-12 items-center justify-center rounded-full border border-gray-700 bg-gray-800 text-gray-400">
								<UploadIcon className="size-6" />
							</div>
							<p className="mb-1 text-lg font-semibold text-white">
								{currentFile ? '文件已就绪' : '上传你的简历'}
							</p>
							<p className="text-sm text-muted-foreground">
								{currentFile
									? currentFile.file.name
									: `拖拽或点击上传（PDF、DOCX，最大 ${formatBytes(
										maxSize,
									)}）`}
							</p>
						</>
					)}
				</div>
			</div>

			{displayErrors.length > 0 &&
				!isUploadingGlobal &&
				(!uploadFeedback || uploadFeedback.type === 'error') && (
					<div
						className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive"
						role="alert"
					>
						<div className="flex items-start gap-2">
							<AlertCircleIcon className="mt-0.5 size-5 shrink-0" />
							<div>
								<p className="font-semibold">错误</p>
								{displayErrors.map((error, index) => (
									<p key={index}>{error}</p>
								))}
							</div>
						</div>
					</div>
				)}

			{uploadFeedback?.type === 'success' && !isUploadingGlobal && (
				<div
					className="rounded-md border border-green-500/50 bg-green-500/10 p-3 text-sm text-green-600"
					role="status"
				>
					<div className="flex items-start gap-2">
						<CheckCircle2Icon className="mt-0.5 size-5 shrink-0" />
						<div>
							<p className="font-semibold">成功</p>
							<p>{uploadFeedback.message}</p>
						</div>
					</div>
				</div>
			)}

			{currentFile && !isUploadingGlobal && (
				<div className="rounded-xl border border-gray-700 bg-background/60 p-4">
					<div className="flex items-center justify-between gap-3">
						<div className="flex min-w-0 items-center gap-3">
							<PaperclipIcon className="size-5 shrink-0 text-muted-foreground" />
							<div className="min-w-0 flex-1">
								<p className="truncate text-sm font-medium text-white">
									{currentFile.file.name}{' '}
									{/* name is on both File and FileMetadata */}
								</p>
								<p className="text-xs text-muted-foreground">
									{formatBytes(currentFile.file.size)} -{' '}
									{/* size is on both File and FileMetadata */}
									{/* After upload attempt, .file is FileMetadata */}
									{(currentFile.file as FileMetadata).uploaded === true
										? '已上传'
										: (currentFile.file as FileMetadata).uploadError
											? '上传失败'
											: '等待上传'}
								</p>
							</div>
						</div>
						<Button
							size="icon"
							variant="ghost"
							className="size-8 shrink-0 text-muted-foreground hover:text-white"
							onClick={() => handleRemoveFile(currentFile.id)}
							aria-label="移除文件"
							disabled={isUploadingGlobal}
						>
							<XIcon className="size-5" />
						</Button>
					</div>
					{/* Display uploadError if it exists on FileMetadata */}
					{(currentFile.file as FileMetadata).uploadError && (
						<p className="mt-2 text-xs text-destructive">
							错误：{(currentFile.file as FileMetadata).uploadError}
						</p>
					)}
				</div>
			)}
		</div>
	);
}
