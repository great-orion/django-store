from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
import requests
import json
from django.db.models import Max
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication
from rest_framework import status
from django.contrib.postgres.search import (
SearchVector,
SearchQuery,
SearchRank
)
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q
from . import serializers
from . import forms
from . import models

# ZarinPal Configuration
ZARINPAL_MERCHANT_ID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
ZARINPAL_REQUEST_URL = 'https://sandbox.zarinpal.com/pg/v4/payment/request.json'
ZARINPAL_VERIFY_URL = 'https://sandbox.zarinpal.com/pg/v4/payment/verify.json'
ZARINPAL_START_PAY_URL = 'https://sandbox.zarinpal.com/pg/StartPay/'


def get_user_ip(request):
    """Get user's IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_cart(request):
    # initializing the cart
    # first time returns {} or may be cart is corrupted from before
    cart = request.session.get('cart', {})
    if not cart or not isinstance(cart, dict):
        cart = {}
    return cart


def add_to_cart(cart, obj):
    if obj.count > 0 and obj.enabled:
        cart[str(obj.id)] = cart.get(str(obj.id), 0) + 1


def remove_from_cart(cart, item_id):
    item_id_str = str(item_id)
    if item_id_str in cart:
        del cart[item_id_str]


def get_cart_total_price(cart):
    total = 0

    if not cart:
        return total

    # Convert string keys to integers safely
    try:
        product_ids = [int(id) for id in cart.keys() if id.isdigit()]
    except (ValueError, TypeError):
        return 0  # Return 0 if any ID is invalid

    if not product_ids:
        return 0

    # Fetch all products in one query
    products = models.Product.objects.filter(id__in=product_ids)
    product_map = {product.id: product for product in products}  # Now keys are int → int

    for id_str, count in cart.items():
        try:
            product_id = int(id_str)
            product = product_map.get(product_id)
            if not product:
                continue  # Skip if product doesn't exist (was deleted, etc.)

            # Handle discount safely
            discount = product.discount or 0  # Treat None as 0

            price = float(product.price)
            count = int(count) if str(count).isdigit() else 0

            total += price * (1 - discount / 100) * count

        except (ValueError, TypeError, AttributeError):
            # Skip any item that causes an error
            continue

    return round(total, 2)  # Optional: round to 2 decimal places


def prepare_cart_data(cart):
    """Helper to calculate cart totals"""
    product_ids = [int(id) for id in cart.keys() if id.isdigit()]
    products = models.Product.objects.filter(id__in=product_ids)

    cart_items = []
    subtotal = 0
    for item_id, count in cart.items():
        try:
            product = products.get(id=int(item_id))
            count = int(count)
            item_total = product.price * count * (1 - product.discount / 100)
            subtotal += product.price * count  # original price
            cart_items.append({
                'product': product,
                'count': count,
                'price': float(product.price),
                'discount': product.discount,
                'total': float(item_total),
            })
        except models.Product.DoesNotExist:
            continue

    discount_total = subtotal - sum(item['total'] for item in cart_items)
    vat_rate = 9
    vat_amount = float(subtotal - discount_total) * vat_rate / 100
    total = (subtotal - discount_total) + vat_amount

    return cart_items, float(subtotal), float(discount_total), vat_amount, total


class ListProducts(View):
    def get(self, request):
        # Filter products: enabled, not deleted, count > 0
        products = models.Product.objects.filter(
            enabled=True,
            deleted=False,
            count__gt=0
        )

        # Get category filter from URL (e.g., ?category=3)
        category_id = request.GET.get('category')
        if category_id:
            try:
                products = products.filter(category_id=category_id)
            except:
                pass  # Ignore invalid category

        # Get all categories (only those that have products and are not deleted)
        categories = models.Category.objects.filter(
            deleted=False
        ).order_by('name')

        context = {
            'products': products,
            'categories': categories,
            'selected_category': category_id,
        }

        return render(request, 'core/product_list.html', context)


class AddToCartView(View):
    def get(self, request, item_id):
        # initializing the cart
        cart = get_cart(request)
        obj = get_object_or_404(models.Product, id=item_id)

        add_to_cart(cart, obj)

        # Save back to session
        request.session['cart'] = cart
        request.session.modified = True  # Force save

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(cart)

        # Redirect to product list
        return HttpResponseRedirect(reverse('core:product_list'))


class RemoveFromCartView(View):
    def post(self, request, item_id):
        cart = get_cart(request)
        remove_from_cart(cart, item_id)
        request.session['cart'] = cart
        request.session.modified = True  # Force save
        total = get_cart_total_price(cart)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'cart': cart, 'total': float(total)})

        return redirect('core:cart_show')


class EmptyCartView(View):
    def get(self, request):
        request.session['cart'] = {}
        request.session.modified = True  # Force save

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({})

        return redirect('core:product_list')


class ShowCartView(View):
    def get(self, request):
        cart = get_cart(request)
        total = get_cart_total_price(cart)

        product_ids = [int(id) for id in cart.keys() if id.isdigit()]
        products = models.Product.objects.filter(id__in=product_ids)

        return render(request, 'core/cart.html',
                      {'cart': cart, 'total': total, 'products': products})


class CheckoutCartView(LoginRequiredMixin, View):
    def get(self, request):
        form = forms.InvoiceForm()
        cart = get_cart(request)
        cart_items, subtotal, discount_total, vat_amount, total = prepare_cart_data(cart)

        return render(request, 'core/checkout.html', {
            'form': form,
            'cart_items': cart_items,
            'subtotal': subtotal,
            'discount_total': discount_total,
            'vat_rate': 9,  # Adjust as needed
            'vat_amount': vat_amount,
            'total': total,
        })

    def post(self, request):
        form = forms.InvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.user = request.user
            cart = get_cart(request)
            invoice.total = get_cart_total_price(cart)
            invoice.save()

            product_ids = [int(id) for id in cart.keys() if id.isdigit()]
            items = models.Product.objects.filter(id__in=product_ids)

            invoice_item = []
            for item_id, item_count in cart.items():
                obj = items.get(id=int(item_id))
                invoice_item_obj = models.InvoiceItem()
                invoice_item_obj.invoice = invoice
                invoice_item_obj.product = obj
                invoice_item_obj.name = obj.name
                invoice_item_obj.count = int(item_count)
                invoice_item_obj.discount = obj.discount
                invoice_item_obj.price = obj.price
                invoice_item_obj.total = (invoice_item_obj.price * invoice_item_obj.count *
                                          (1 - invoice_item_obj.discount / 100))
                invoice_item.append(invoice_item_obj)

            models.InvoiceItem.objects.bulk_create(invoice_item)  # save to db

            payment = models.Payment()
            payment.invoice = invoice
            payment.total = invoice.total * (1 - invoice.discount / 100)
            payment.total += (invoice.vat / 100) * payment.total
            payment.user_ip = get_user_ip(request)

            # Prepare callback URL
            callback_url = request.build_absolute_uri(reverse('core:verify'))

            # Prepare request data for ZarinPal
            request_data = {
                'merchant_id': ZARINPAL_MERCHANT_ID,
                'amount': int(payment.total),
                'currency': 'IRT',
                'description': f'invoice, No. {invoice.id}',
                'callback_url': callback_url,
                'metadata': {
                    'email': request.user.email,
                }
            }

            # Make request to ZarinPal
            try:
                response = requests.post(
                    ZARINPAL_REQUEST_URL,
                    data=json.dumps(request_data),
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    timeout=30
                )

                response_data = response.json()

                if response_data.get('data', {}).get('code') == 100:
                    # Success - redirect to ZarinPal
                    authority = response_data['data']['authority']

                    # Store authority in payment record
                    payment.authority = authority
                    payment.save()

                    # Redirect to ZarinPal payment page
                    payment_url = f"{ZARINPAL_START_PAY_URL}{authority}"
                    return redirect(payment_url)

                else:
                    # Payment request failed
                    error_code = response_data.get('errors', {}).get('code', 'Unknown')
                    error_message = response_data.get('errors', {}).get('message', 'unknown error in payment')

                    payment.status = payment.STATUS_ERROR
                    payment.error_code = str(error_code)
                    payment.error_message = error_message
                    payment.save()

                    return render(request, 'core/checkout_error.html', {'msg': error_message})


            except Exception as e:
                # Network or connection error
                payment.status = payment.STATUS_ERROR
                payment.error_message = f'error in connection to zarinpal: {str(e)}'
                payment.save()
                error_message = "Couldn't connect to zarinpal. please try again later!"
                return render(request, 'core/checkout_error.html', {'msg': error_message})

        return render(request, 'core/checkout.html', {'form': form})


class VerifyView(View):
    """
    Verify payment with ZarinPal
    """

    def get(self, request):
        # Get the query parameters from ZarinPal
        status = request.GET.get('Status')
        authority = request.GET.get('Authority')

        # Validate the received parameters
        if not authority:
            return render(request, 'core/payment_failed.html', {
                'reason': 'Payment was cancelled!'
            })

        # Find the corresponding payment in your database
        try:
            payment = models.Payment.objects.get(authority=authority, status=models.Payment.STATUS_PENDING)
        except models.Payment.DoesNotExist:
            return render(request, 'core/payment_failed.html', {
                'reason': 'There is no payment document!'
            })

        # Check if the user canceled the payment
        if status != 'OK':
            payment.status = payment.STATUS_ERROR
            payment.save()
            return render(request, 'core/payment_failed.html', {
                'reason': 'Payment was canceled by the user.'
            })

        # Verify the payment with ZarinPal's server
        verify_data = {
            "merchant_id": ZARINPAL_MERCHANT_ID,
            "amount": int(payment.total),  # Must match the amount in the request
            "authority": authority
        }
        headers = {'Content-Type': 'application/json'}

        try:
            verify_response = requests.post(
                ZARINPAL_VERIFY_URL,
                data=json.dumps(verify_data),
                headers=headers
            )
            verify_result = verify_response.json()
        except requests.exceptions.RequestException as e:
            # Handle network errors during verification
            return render(request, 'core/payment_failed.html', {
                'reason': 'Network error!'
            })

        # Check the verification result
        # A successful verification has a 'data' object with 'ref_id'
        if verify_result.get('data').get('code') == 100:
            ref_id = verify_result['data']['ref_id']

            # Update your payment and invoice records
            payment.ref = ref_id
            payment.status = payment.STATUS_DONE
            payment.save()

            # Get the invoice
            invoice = payment.invoice

            # Assign unique, continuous invoice number
            if invoice.number is None:
                max_number = models.Invoice.objects.aggregate(Max('number'))['number__max']
                invoice.number = (max_number or 0) + 1

            # Update product counts
            invoice_items = models.InvoiceItem.objects.filter(invoice=invoice)
            for item in invoice_items:
                product = item.product
                product.count -= item.count
                product.save()

            invoice.save()

            # empty cart
            request.session['cart'] = {}
            request.session.Modified = True

            return render(request, 'core/payment_success.html', {
                'ref_id': ref_id,
                'amount': int(payment.total)
            })

        else:
            # we can log the error (we had to check code 101)
            payment.status = payment.STATUS_ERROR
            payment.save()
            return render(request, 'core/payment_failed.html', {
                'reason': 'Payment not verified!!'
            })


class SearchView(View):
    def get(self, request):
        form = forms.SearchForm()
        query = None
        results = []

        if 'query' in request.GET:
            form = forms.SearchForm(request.GET)
            if form.is_valid():
                query = form.cleaned_data['query']
                search_vector = SearchVector('name', 'description', 'category__name', config='english')
                search_query = SearchQuery(query, config='english')

                results = (
                    models.Product.objects.annotate(
                        search=search_vector,
                        rank=SearchRank(search_vector, search_query),
                        similarity=(
                                TrigramSimilarity('name', query) * 1.5 +
                                TrigramSimilarity('description', query) +
                                TrigramSimilarity('category__name', query) * 0.8
                        )
                    )
                    .filter(
                        Q(search=search_query) | Q(similarity__gt=0.1)
                    )
                    .order_by('-rank', '-similarity')
                )

        return render(
            request,
            'core/product_list.html',
            {
                'form': form,
                'query': query,
                'results': results,
            }
        )

class ProductListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request, format=None):
        obj = models.Product.objects.all()
        s = serializers.ProductListSerializer(obj, many=True)
        return Response(s.data)


# ADD TO CART WITH API

# class AddToCartAPIView(APIView):
#     def post(self, request):
#         s = serializers.AddToCartSerializer(data=request.data)
#         if s.is_valid():
#             try:
#                 id = s.validated_data['product_id']
#                 obj = models.Product.objects.get(id=id)
#                 cart = get_cart(request)
#                 add_to_cart(cart, obj)
#                 # Save back to session
#                 request.session['cart'] = cart
#                 request.session.modified = True  # Force save
#
#                 if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#                     return JsonResponse(cart)
#
#                 # Redirect to product list
#                 return HttpResponseRedirect(reverse('core:product_list'))
#
#             except models.Product.DoesNotExist:
#                 return Response({'error': 'product not found'}, status.HTTP_404_NOT_FOUND)
#
#         return Response({'error': 'bad request'}, status.HTTP_400_BAD_REQUEST)
#
#
# class GetCartAPIView(APIView):
#     permission_classes = [AllowAny]
#     authentication_classes = []
#
#     def get(self, request):
#         cart = get_cart(request)
#         d = []
#         for id, count in cart.items():
#             d.append({'id': id, 'count': count})
#
#         s = serializers.CartSerializer(instance=d, many=True)
#         return Response(s.data)