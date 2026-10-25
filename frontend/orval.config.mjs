export default {
  api: {
    hooks: {
      afterAllFilesWrite: 'prettier --write',
    },
    output: {
      target: './src/api',
      client: 'react-query',
      mode: 'tags-split',
      override: {
        mutator: './src/api/client.ts',
        query: {
          version: 5,
          useQuery: true,
          useMutation: true,
          shouldExportHttpClient: true,
          shouldExportMutatorHooks: false,
        },
      },
    },
    input: { target: '../openapi.json' },
  },
}
