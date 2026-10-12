export interface SceneDetails {
  title: string;
  filePath: string;
}

export const SCENE_DETAILS: Record<string, SceneDetails> = {
  hook: { title: 'Headline hook', filePath: 'src/components/video/video_scenes/Scene1.tsx' },
  pathways: { title: 'Three pathways', filePath: 'src/components/video/video_scenes/Scene2.tsx' },
  exchanges: { title: 'Six exchanges', filePath: 'src/components/video/video_scenes/Scene3.tsx' },
  fit: { title: 'Solution fit & review', filePath: 'src/components/video/video_scenes/Scene4.tsx' },
  dashboard: { title: 'Opportunity Dashboard', filePath: 'src/components/video/video_scenes/Scene5.tsx' },
  lockup: { title: 'Lockup', filePath: 'src/components/video/video_scenes/Scene6.tsx' },
};
