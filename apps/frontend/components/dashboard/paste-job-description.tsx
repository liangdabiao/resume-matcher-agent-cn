'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea'; // Assuming you have a Textarea component
import { XIcon, ClipboardPasteIcon } from 'lucide-react';

interface PasteJobDescriptionProps {
	onClose: () => void;
	onPaste: (text: string) => void;
}

export default function PasteJobDescription({ onClose, onPaste }: PasteJobDescriptionProps) {
	const [jobDescription, setJobDescription] = useState('');
	const [error, setError] = useState<string | null>(null);

	const handlePaste = () => {
		if (!jobDescription.trim()) {
			setError('岗位描述不能为空。');
			return;
		}
		setError(null);
		onPaste(jobDescription);
		onClose(); // Close modal after pasting
	};

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
			<div className="relative w-full max-w-2xl rounded-xl bg-gray-800 p-6 shadow-xl">
				<div className="flex items-center justify-between pb-4 border-b border-gray-700">
					<h3 className="text-lg font-semibold text-white">粘贴岗位描述</h3>
					<Button
						size="icon"
						variant="ghost"
						className="text-muted-foreground/80 hover:text-foreground -me-2 size-9 hover:bg-transparent"
						onClick={onClose}
						aria-label="关闭弹窗"
					>
						<XIcon className="size-5" aria-hidden="true" />
					</Button>
				</div>

				<div className="py-6">
					<div className="flex flex-col items-center justify-center text-center mb-4">
						<div
							className="bg-white mb-3 flex size-12 shrink-0 items-center justify-center rounded-full border"
							aria-hidden="true"
						>
							<ClipboardPasteIcon className="size-5 opacity-60" />
						</div>
						<p className="mb-2 text-lg font-semibold text-white">
							粘贴岗位描述
						</p>
						<p className="text-muted-foreground text-sm">
							请在下方粘贴完整岗位描述。
						</p>
					</div>

					<Textarea
						value={jobDescription}
						onChange={(e) => {
							setJobDescription(e.target.value);
							if (error) setError(null);
						}}
						placeholder="请粘贴岗位描述..."
						className="w-full min-h-[200px] rounded-md border-gray-600 bg-gray-700 p-3 text-white focus:ring-blue-500 focus:border-blue-500"
						aria-label="岗位描述输入框"
					/>
					{error && (
						<p className="text-destructive mt-2 text-xs" role="alert">
							{error}
						</p>
					)}
				</div>

				<div className="flex justify-end gap-3 pt-4 border-t border-gray-700">
					<Button
						variant="outline"
						onClick={onClose}
						className="text-white border-gray-600 hover:bg-gray-700"
					>
						取消
					</Button>
					<Button
						onClick={handlePaste}
						className="bg-blue-600 hover:bg-blue-700 text-white"
					>
						保存岗位描述
					</Button>
				</div>
			</div>
		</div>
	);
}
