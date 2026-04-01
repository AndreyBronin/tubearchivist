import APIClient from '../../functions/APIClient';

export type CreateVideoClipRequest = {
  segments: string;
  title?: string;
};

export type CreateVideoClipResponse = {
  message: string;
};

const createVideoClip = async (videoId: string, data: CreateVideoClipRequest) => {
  return APIClient<CreateVideoClipResponse>(`/api/video/${videoId}/cut/`, {
    method: 'POST',
    body: data as Record<string, unknown>,
  });
};

export default createVideoClip;
