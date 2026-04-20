import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/features/subscription/data/datasources/subscription_remote_ds.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockApiClient extends Mock implements ApiClient {}

void main() {
  late MockApiClient mockApiClient;
  late SubscriptionRemoteDataSourceImpl dataSource;

  setUp(() {
    mockApiClient = MockApiClient();
    dataSource = SubscriptionRemoteDataSourceImpl(mockApiClient);
  });

  RequestOptions requestOptions(String path) => RequestOptions(path: path);

  group('fetchActiveSubscription', () {
    test(
      'maps canonical entitlements and service-state into SubscriptionEntity',
      () async {
        when(
          () => mockApiClient.get<Map<String, dynamic>>(
            ApiConstants.activeSubscription,
            queryParameters: any<Map<String, dynamic>?>(
              named: 'queryParameters',
            ),
            options: any<Options?>(named: 'options'),
            cancelToken: any<CancelToken?>(named: 'cancelToken'),
          ),
        ).thenAnswer(
          (_) async => Response(
            data: {
              'status': 'active',
              'plan_uuid': 'plan-pro-uuid',
              'plan_code': 'pro',
              'display_name': 'Pro Annual',
              'period_days': 365,
              'expires_at': '2027-04-19T00:00:00Z',
              'effective_entitlements': {
                'device_limit': 5,
                'display_traffic_label': '200 GB',
              },
              'invite_bundle': {'count': 0, 'friend_days': 0, 'expiry_days': 0},
              'is_trial': false,
              'addons': const [],
            },
            statusCode: 200,
            requestOptions: requestOptions(ApiConstants.activeSubscription),
          ),
        );

        when(
          () => mockApiClient.post<Map<String, dynamic>>(
            ApiConstants.currentServiceState,
            data: const {'provider_name': 'remnawave'},
            options: any<Options?>(named: 'options'),
            cancelToken: any<CancelToken?>(named: 'cancelToken'),
          ),
        ).thenAnswer(
          (_) async => Response(
            data: {
              'customer_account_id': 'customer-1',
              'service_identity': {'id': 'service-identity-1'},
              'purchase_context': {'active_entitlement_grant_id': 'grant-1'},
              'provisioning_profile': {
                'provisioning_payload': {
                  'subscription_url':
                      'https://vpn.example/subscription/grant-1',
                },
              },
              'access_delivery_channel': {
                'delivery_payload': {
                  'config_url': 'https://vpn.example/config/grant-1',
                },
              },
            },
            statusCode: 200,
            requestOptions: requestOptions(ApiConstants.currentServiceState),
          ),
        );

        final subscription = await dataSource.fetchActiveSubscription();

        expect(subscription, isNotNull);
        expect(subscription!.id, 'grant-1');
        expect(subscription.planId, 'plan-pro-uuid');
        expect(subscription.userId, 'customer-1');
        expect(subscription.status, SubscriptionStatus.active);
        expect(subscription.maxDevices, 5);
        expect(subscription.trafficLimitBytes, 200 * 1024 * 1024 * 1024);
        expect(
          subscription.subscriptionLink,
          'https://vpn.example/config/grant-1',
        );
      },
    );

    test(
      'returns null when canonical entitlements report no active access',
      () async {
        when(
          () => mockApiClient.get<Map<String, dynamic>>(
            ApiConstants.activeSubscription,
            queryParameters: any<Map<String, dynamic>?>(
              named: 'queryParameters',
            ),
            options: any<Options?>(named: 'options'),
            cancelToken: any<CancelToken?>(named: 'cancelToken'),
          ),
        ).thenAnswer(
          (_) async => Response(
            data: {
              'status': 'none',
              'effective_entitlements': {'device_limit': 0},
              'invite_bundle': const {},
              'is_trial': false,
              'addons': const [],
            },
            statusCode: 200,
            requestOptions: requestOptions(ApiConstants.activeSubscription),
          ),
        );

        final subscription = await dataSource.fetchActiveSubscription();

        expect(subscription, isNull);
        verifyNever(
          () => mockApiClient.post<Map<String, dynamic>>(
            any(),
            data: any<dynamic>(named: 'data'),
            options: any<Options?>(named: 'options'),
            cancelToken: any<CancelToken?>(named: 'cancelToken'),
          ),
        );
      },
    );
  });

  group('fetchPaymentHistory', () {
    test('maps canonical orders into payment history entries', () async {
      when(
        () => mockApiClient.get<List<dynamic>>(
          ApiConstants.paymentHistory,
          queryParameters: {'offset': 0, 'limit': 20},
          options: any<Options?>(named: 'options'),
          cancelToken: any<CancelToken?>(named: 'cancelToken'),
        ),
      ).thenAnswer(
        (_) async => Response(
          data: [
            {
              'id': 'order-1',
              'currency_code': 'USD',
              'order_status': 'committed',
              'settlement_status': 'paid',
              'displayed_price': 99.99,
              'created_at': '2026-04-18T12:00:00Z',
              'items': [
                {'display_name': 'Annual Pro'},
              ],
            },
            {
              'id': 'order-2',
              'currency_code': 'USD',
              'order_status': 'committed',
              'settlement_status': 'refunded',
              'displayed_price': 9.99,
              'created_at': '2026-04-17T12:00:00Z',
              'items': [
                {'display_name': 'Monthly Pro'},
              ],
            },
          ],
          statusCode: 200,
          requestOptions: requestOptions(ApiConstants.paymentHistory),
        ),
      );

      final history = await dataSource.fetchPaymentHistory();

      expect(history.total, 2);
      expect(history.items, hasLength(2));
      expect(history.items.first.id, 'order-1');
      expect(history.items.first.planName, 'Annual Pro');
      expect(history.items.first.amount, 99.99);
      expect(history.items.first.status, 'paid');
      expect(history.items.last.status, 'refunded');
    });
  });
}
