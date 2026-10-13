import type { paths } from '../../types/api.generated'

export type HttpMethod = 'get' | 'post' | 'patch' | 'put' | 'delete'

type OperationAt<
  Path extends keyof paths,
  Method extends HttpMethod,
> = NonNullable<paths[Path][Method]>

type JsonRequestBody<Operation> = Operation extends {
  requestBody: { content: { 'application/json': infer Body } }
}
  ? Body
  : never

type JsonResponseBody<Response> = Response extends {
  content: { 'application/json': infer Body }
}
  ? Body
  : never

type SuccessfulResponseBody<Responses> = {
  [Status in keyof Responses]: Status extends number
    ? `${Status}` extends `2${number}`
      ? JsonResponseBody<Responses[Status]>
      : never
    : never
}[keyof Responses]

type MultipartRequestBody<Operation> = Operation extends {
  requestBody: { content: { 'multipart/form-data': infer Body } }
}
  ? Body
  : never

export type RequestBodyOf<
  Path extends keyof paths,
  Method extends HttpMethod,
> = JsonRequestBody<OperationAt<Path, Method>>

export type MultipartRequestBodyOf<
  Path extends keyof paths,
  Method extends HttpMethod,
> = MultipartRequestBody<OperationAt<Path, Method>>

export type QueryParametersOf<
  Path extends keyof paths,
  Method extends HttpMethod,
> = NonNullable<OperationAt<Path, Method>['parameters']['query']>

export type ResponseBodyOf<
  Path extends keyof paths,
  Method extends HttpMethod,
> = OperationAt<Path, Method> extends { responses: infer Responses }
  ? SuccessfulResponseBody<Responses>
  : never

export type QueryValue = string | number | boolean | null | undefined
export type ScalarQuery = Record<string, QueryValue>

export type PathParameter<Path extends keyof paths> = NonNullable<paths[Path]['parameters']['path']>
