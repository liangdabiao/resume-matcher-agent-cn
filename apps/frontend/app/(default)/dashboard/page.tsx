// File: apps/frontend/app/dashboard/page.tsx


'use client';

import React from 'react';
import BackgroundContainer from '@/components/common/background-container';
import JobListings from '@/components/dashboard/job-listings';
import { useResumePreview } from '@/components/common/resume_previewer_context';


const escapeHtml = (value: string): string =>
	value
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&#39;');

const safeHref = (value: string): string => {
	const href = value.trim();
	return /^(https?:\/\/|mailto:|\/)/i.test(href) ? escapeHtml(href) : '#';
};

const renderInlineMarkdown = (value: string): string => {
	let html = escapeHtml(value);

	html = html.replace(/`([^`]+)`/g, '<code class="rounded bg-gray-950/80 px-1.5 py-0.5 text-xs text-pink-200">$1</code>');
	html = html.replace(/\[([^\]]+)]\(([^)]+)\)/g, (_match, label: string, href: string) => {
		return `<a href="${safeHref(href)}" class="text-blue-300 underline-offset-4 hover:underline" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`;
	});
	html = html.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-white">$1</strong>');
	html = html.replace(/(^|\s)\*([^*]+)\*/g, '$1<em class="italic text-gray-100">$2</em>');

	return html;
};

const convertMarkdownToHtml = (markdown: string): string => {
	const lines = markdown.replace(/\r\n/g, '\n').split('\n');
	const blocks: string[] = [];
	let listType: 'ul' | 'ol' | null = null;
	let paragraph: string[] = [];

	const closeList = () => {
		if (!listType) return;
		blocks.push(`</${listType}>`);
		listType = null;
	};

	const flushParagraph = () => {
		if (paragraph.length === 0) return;
		blocks.push(`<p class="mb-4 leading-7 text-gray-200">${renderInlineMarkdown(paragraph.join(' '))}</p>`);
		paragraph = [];
	};

	const openList = (type: 'ul' | 'ol') => {
		if (listType === type) return;
		closeList();
		listType = type;
		const className = type === 'ul'
			? 'my-4 ml-5 list-disc space-y-2 text-gray-200 marker:text-purple-300'
			: 'my-4 ml-5 list-decimal space-y-2 text-gray-200 marker:text-purple-300';
		blocks.push(`<${type} class="${className}">`);
	};

	for (const rawLine of lines) {
		const line = rawLine.trim();

		if (!line) {
			flushParagraph();
			closeList();
			continue;
		}

		const headingMatch = line.match(/^(#{1,6})\s+(.+?)\s*#*$/);
		if (headingMatch) {
			flushParagraph();
			closeList();

			const level = headingMatch[1].length;
			const content = renderInlineMarkdown(headingMatch[2]);
			const headingClasses: Record<number, string> = {
				1: 'mt-0 mb-5 border-b border-purple-400/30 pb-3 text-3xl font-bold tracking-tight text-white',
				2: 'mt-8 mb-4 border-b border-gray-700 pb-2 text-2xl font-bold text-purple-100',
				3: 'mt-6 mb-3 text-xl font-semibold text-pink-100',
				4: 'mt-5 mb-2 text-lg font-semibold text-blue-100',
				5: 'mt-4 mb-2 text-base font-semibold text-gray-100',
				6: 'mt-4 mb-2 text-sm font-semibold uppercase tracking-wide text-gray-300',
			};
			blocks.push(`<h${level} class="${headingClasses[level]}">${content}</h${level}>`);
			continue;
		}

		const unorderedMatch = line.match(/^[-*+]\s+(.+)$/);
		if (unorderedMatch) {
			flushParagraph();
			openList('ul');
			blocks.push(`<li class="leading-7">${renderInlineMarkdown(unorderedMatch[1])}</li>`);
			continue;
		}

		const orderedMatch = line.match(/^\d+[.)]\s+(.+)$/);
		if (orderedMatch) {
			flushParagraph();
			openList('ol');
			blocks.push(`<li class="leading-7">${renderInlineMarkdown(orderedMatch[1])}</li>`);
			continue;
		}

		closeList();
		paragraph.push(line);
	}

	flushParagraph();
	closeList();

	return blocks.join('\n');
};

export default function DashboardPage() {
	const { improvedData } = useResumePreview();
	if (!improvedData) {
		return (
			<BackgroundContainer className="min-h-screen" innerClassName="bg-zinc-950">
				<div className="flex items-center justify-center h-full p-6 text-gray-400">
					暂未找到优化结果。请先在岗位描述页面点击“开始优化”。
				</div>
			</BackgroundContainer>
		);
	}

	const { data } = improvedData;
	
	const analysisResult = data.analysis_result ?? '暂无分析结果。';


	return (
		<BackgroundContainer className="min-h-screen" innerClassName="bg-zinc-950 backdrop-blur-sm overflow-auto">
			<div className="w-full h-full overflow-auto py-8 px-4 sm:px-6 lg:px-8">
				<div className="container mx-auto">
					<div className="mb-10">
						<h1 className="text-3xl font-semibold pb-2 text-white">
											<span className="bg-gradient-to-r from-pink-400 to-purple-400 text-transparent bg-clip-text">
								简历匹配智能体
							</span>{' '}
							控制台
						</h1>
						<p className="text-gray-300 text-lg">
							查看岗位匹配结果、简历审计报告和优化建议。
						</p>
					</div>

					<div className="grid grid-cols-1 md:grid-cols-3 gap-8">
						<div className="space-y-8">
							<section>
								<JobListings resumeId={data.resume_id} />
							</section>
						</div>

						<div className="md:col-span-2">
							<div className="bg-gray-900/70 backdrop-blur-sm p-6 rounded-lg shadow-xl h-full flex flex-col border border-gray-800/50">
								<div className="mb-6">
									<h2 className="text-2xl font-bold text-white mb-1">分析结果</h2>
									<p className="text-gray-400 text-sm">
										以下是你的简历与目标岗位的匹配分析。
									</p>
								</div>
								<div className="flex-grow overflow-auto">
									<div className="bg-gray-800/50 p-4 rounded-lg h-full">
										<div 
											className="prose prose-invert max-w-none text-gray-200 text-sm"
											dangerouslySetInnerHTML={{ __html: convertMarkdownToHtml(analysisResult) }}
										/>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</BackgroundContainer>
	);
}
