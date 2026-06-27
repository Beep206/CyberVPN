import { NextRequest } from 'next/server';

import { proxyApiRequest } from '../../_shared/proxy';
import type { ApiProxyRouteContext } from '../../_shared/proxy';

const API_BASE_PATH = '/api/v3';

export function GET(request: NextRequest, context: ApiProxyRouteContext) {
  return proxyApiRequest(request, context, API_BASE_PATH);
}

export function POST(request: NextRequest, context: ApiProxyRouteContext) {
  return proxyApiRequest(request, context, API_BASE_PATH);
}

export function PUT(request: NextRequest, context: ApiProxyRouteContext) {
  return proxyApiRequest(request, context, API_BASE_PATH);
}

export function PATCH(request: NextRequest, context: ApiProxyRouteContext) {
  return proxyApiRequest(request, context, API_BASE_PATH);
}

export function DELETE(request: NextRequest, context: ApiProxyRouteContext) {
  return proxyApiRequest(request, context, API_BASE_PATH);
}

export function HEAD(request: NextRequest, context: ApiProxyRouteContext) {
  return proxyApiRequest(request, context, API_BASE_PATH);
}

export function OPTIONS(request: NextRequest, context: ApiProxyRouteContext) {
  return proxyApiRequest(request, context, API_BASE_PATH);
}
