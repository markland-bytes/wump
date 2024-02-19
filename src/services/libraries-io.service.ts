import { LibrariesIO } from 'libraries.io';

export const librariesIOService = (apiKey: string) => {
    if (!apiKey) {
        throw new Error('Missing LIBRARIES_IO_API_KEY');
    }
    const librariesIO = new LibrariesIO(apiKey);
    
    return {
        getProject: librariesIO.api.project.getProject,
        searchProject: librariesIO.api.project.search,
        getUser: librariesIO.api.github.user.getUser,
        getPlatforms: librariesIO.api.platform.getPlatforms,
    };
};
