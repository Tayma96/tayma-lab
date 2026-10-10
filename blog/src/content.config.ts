import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const posts = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/posts' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    date: z.coerce.date(),
    updated: z.coerce.date().optional(),
    category: z.string().default('Genel'),
    tags: z.array(z.string()).default([]),
    draft: z.boolean().default(false),
    aiGenerated: z.boolean().default(false),
    sources: z.array(z.object({ title: z.string(), url: z.string() })).default([]),
  }),
});

export const collections = { posts };
