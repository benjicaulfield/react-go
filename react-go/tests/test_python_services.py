#!/usr/bin/env python3
"""
Comprehensive Python Services Endpoint Testing
Tests the Python recommendation microservice endpoints thoroughly.
"""

import requests
import json
import time
import sys
import threading
from typing import Dict, List, Any
import subprocess
import signal
import os

class PythonServiceTester:
    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url
        self.test_results = []
        self.service_process = None
        
    def start_service(self):
        """Start the Python recommendation service for testing"""
        try:
            print("🚀 Starting Python recommendation service...")
            self.service_process = subprocess.Popen(
                [sys.executable, "python-services/recommendation-service.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # Give the service time to start
            time.sleep(2)
            return True
        except Exception as e:
            print(f"❌ Failed to start service: {e}")
            return False
    
    def stop_service(self):
        """Stop the Python recommendation service"""
        if self.service_process:
            self.service_process.terminate()
            self.service_process.wait()
            print("🛑 Python recommendation service stopped")
    
    def make_request(self, method: str, endpoint: str, data: Dict = None, timeout: int = 10) -> Dict[str, Any]:
        """Make HTTP request to the service"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, timeout=timeout)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return {
                "status_code": response.status_code,
                "data": response.json() if response.content else {},
                "success": True,
                "error": None
            }
        except requests.exceptions.RequestException as e:
            return {
                "status_code": None,
                "data": {},
                "success": False,
                "error": str(e)
            }
        except json.JSONDecodeError as e:
            return {
                "status_code": response.status_code if 'response' in locals() else None,
                "data": {},
                "success": False,
                "error": f"JSON decode error: {e}"
            }
    
    def test_health_endpoint(self):
        """Test the health check endpoint"""
        print("\n🔍 Testing Health Endpoint...")
        
        result = self.make_request("GET", "/health")
        
        test_case = {
            "name": "GET /health - Health Check",
            "passed": False,
            "details": {}
        }
        
        if result["success"]:
            if result["status_code"] == 200:
                data = result["data"]
                if "status" in data and data["status"] == "healthy":
                    test_case["passed"] = True
                    test_case["details"] = {
                        "status_code": result["status_code"],
                        "response": data,
                        "message": "Health check passed"
                    }
                else:
                    test_case["details"] = {
                        "status_code": result["status_code"],
                        "response": data,
                        "error": "Health status not 'healthy'"
                    }
            else:
                test_case["details"] = {
                    "status_code": result["status_code"],
                    "error": f"Expected 200, got {result['status_code']}"
                }
        else:
            test_case["details"] = {
                "error": result["error"],
                "message": "Failed to connect to service"
            }
        
        self.test_results.append(test_case)
        print(f"{'✅' if test_case['passed'] else '❌'} {test_case['name']}")
        
        return test_case["passed"]
    
    def test_predict_endpoint(self):
        """Test the prediction endpoint with various scenarios"""
        print("\n🔍 Testing Prediction Endpoint...")
        
        test_cases = [
            {
                "name": "POST /predict - Valid Listing IDs",
                "data": {"listing_ids": [1, 2, 3, 4, 5]},
                "expected_status": 200,
                "should_have_predictions": True
            },
            {
                "name": "POST /predict - Single Listing ID",
                "data": {"listing_ids": [1]},
                "expected_status": 200,
                "should_have_predictions": True
            },
            {
                "name": "POST /predict - Empty Listing IDs",
                "data": {"listing_ids": []},
                "expected_status": 200,
                "should_have_predictions": False
            },
            {
                "name": "POST /predict - No Listing IDs Key",
                "data": {},
                "expected_status": 200,
                "should_have_predictions": False
            },
            {
                "name": "POST /predict - Large Number of IDs",
                "data": {"listing_ids": list(range(1, 101))},  # 100 IDs
                "expected_status": 200,
                "should_have_predictions": True
            },
            {
                "name": "POST /predict - Mixed Valid/Invalid IDs",
                "data": {"listing_ids": [1, "invalid", 3, None, 5]},
                "expected_status": 200,
                "should_have_predictions": True  # Should handle gracefully
            }
        ]
        
        for test_case in test_cases:
            result = self.make_request("POST", "/predict", test_case["data"])
            
            test_result = {
                "name": test_case["name"],
                "passed": False,
                "details": {}
            }
            
            if result["success"]:
                if result["status_code"] == test_case["expected_status"]:
                    data = result["data"]
                    
                    # Check response structure
                    if "predictions" in data:
                        predictions = data["predictions"]
                        
                        if test_case["should_have_predictions"]:
                            if len(predictions) > 0:
                                # Verify prediction structure
                                valid_predictions = True
                                for pred in predictions:
                                    if not all(key in pred for key in ["id", "prediction", "probability"]):
                                        valid_predictions = False
                                        break
                                    if not isinstance(pred["probability"], (int, float)):
                                        valid_predictions = False
                                        break
                                    if not isinstance(pred["prediction"], bool):
                                        valid_predictions = False
                                        break
                                
                                if valid_predictions:
                                    test_result["passed"] = True
                                    test_result["details"] = {
                                        "status_code": result["status_code"],
                                        "predictions_count": len(predictions),
                                        "sample_prediction": predictions[0] if predictions else None,
                                        "message": "Predictions returned with valid structure"
                                    }
                                else:
                                    test_result["details"] = {
                                        "status_code": result["status_code"],
                                        "error": "Invalid prediction structure",
                                        "predictions": predictions[:3]  # Show first 3 for debugging
                                    }
                            else:
                                test_result["details"] = {
                                    "status_code": result["status_code"],
                                    "error": "Expected predictions but got empty list",
                                    "response": data
                                }
                        else:
                            # Should not have predictions
                            if len(predictions) == 0:
                                test_result["passed"] = True
                                test_result["details"] = {
                                    "status_code": result["status_code"],
                                    "message": "Correctly returned empty predictions",
                                    "response": data
                                }
                            else:
                                test_result["details"] = {
                                    "status_code": result["status_code"],
                                    "error": "Expected empty predictions but got results",
                                    "predictions_count": len(predictions)
                                }
                    else:
                        test_result["details"] = {
                            "status_code": result["status_code"],
                            "error": "Response missing 'predictions' key",
                            "response": data
                        }
                else:
                    test_result["details"] = {
                        "status_code": result["status_code"],
                        "error": f"Expected {test_case['expected_status']}, got {result['status_code']}",
                        "response": result["data"]
                    }
            else:
                test_result["details"] = {
                    "error": result["error"],
                    "message": "Failed to make request"
                }
            
            self.test_results.append(test_result)
            print(f"{'✅' if test_result['passed'] else '❌'} {test_result['name']}")
    
    def test_train_endpoint(self):
        """Test the training endpoint with various scenarios"""
        print("\n🔍 Testing Training Endpoint...")
        
        test_cases = [
            {
                "name": "POST /train - Valid Training Data",
                "data": {
                    "listing_ids": [1, 2, 3, 4, 5],
                    "keeper_ids": [1, 3, 5]
                },
                "expected_status": 200
            },
            {
                "name": "POST /train - All Keepers",
                "data": {
                    "listing_ids": [1, 2, 3],
                    "keeper_ids": [1, 2, 3]
                },
                "expected_status": 200
            },
            {
                "name": "POST /train - No Keepers",
                "data": {
                    "listing_ids": [1, 2, 3, 4, 5],
                    "keeper_ids": []
                },
                "expected_status": 200
            },
            {
                "name": "POST /train - Empty Listing IDs",
                "data": {
                    "listing_ids": [],
                    "keeper_ids": []
                },
                "expected_status": 200,
                "should_fail": True
            },
            {
                "name": "POST /train - Missing Listing IDs",
                "data": {
                    "keeper_ids": [1, 2]
                },
                "expected_status": 200,
                "should_fail": True
            },
            {
                "name": "POST /train - Large Dataset",
                "data": {
                    "listing_ids": list(range(1, 201)),  # 200 IDs
                    "keeper_ids": list(range(1, 101))    # 100 keepers
                },
                "expected_status": 200
            }
        ]
        
        for test_case in test_cases:
            result = self.make_request("POST", "/train", test_case["data"])
            
            test_result = {
                "name": test_case["name"],
                "passed": False,
                "details": {}
            }
            
            if result["success"]:
                if result["status_code"] == test_case["expected_status"]:
                    data = result["data"]
                    
                    should_fail = test_case.get("should_fail", False)
                    
                    if should_fail:
                        # Should return success=False
                        if "success" in data and not data["success"]:
                            test_result["passed"] = True
                            test_result["details"] = {
                                "status_code": result["status_code"],
                                "message": "Correctly failed for invalid input",
                                "response": data
                            }
                        else:
                            test_result["details"] = {
                                "status_code": result["status_code"],
                                "error": "Expected failure but got success",
                                "response": data
                            }
                    else:
                        # Should succeed
                        if "success" in data and data["success"]:
                            # Check for required fields
                            if "accuracy" in data and "message" in data:
                                accuracy = data["accuracy"]
                                if isinstance(accuracy, (int, float)) and 0 <= accuracy <= 1:
                                    test_result["passed"] = True
                                    test_result["details"] = {
                                        "status_code": result["status_code"],
                                        "accuracy": accuracy,
                                        "message": data["message"],
                                        "training_successful": True
                                    }
                                else:
                                    test_result["details"] = {
                                        "status_code": result["status_code"],
                                        "error": f"Invalid accuracy value: {accuracy}",
                                        "response": data
                                    }
                            else:
                                test_result["details"] = {
                                    "status_code": result["status_code"],
                                    "error": "Missing required fields (accuracy, message)",
                                    "response": data
                                }
                        else:
                            test_result["details"] = {
                                "status_code": result["status_code"],
                                "error": "Training failed unexpectedly",
                                "response": data
                            }
                else:
                    test_result["details"] = {
                        "status_code": result["status_code"],
                        "error": f"Expected {test_case['expected_status']}, got {result['status_code']}",
                        "response": result["data"]
                    }
            else:
                test_result["details"] = {
                    "error": result["error"],
                    "message": "Failed to make request"
                }
            
            self.test_results.append(test_result)
            print(f"{'✅' if test_result['passed'] else '❌'} {test_result['name']}")
    
    def test_thermodynamic_endpoint(self):
        """Test the thermodynamic selection endpoint"""
        print("\n🔍 Testing Thermodynamic Selection Endpoint...")
        
        test_cases = [
            {
                "name": "POST /thermodynamic - Normal Selection",
                "data": {"force_refresh": False},
                "expected_status": 200
            },
            {
                "name": "POST /thermodynamic - Force Refresh",
                "data": {"force_refresh": True},
                "expected_status": 200
            },
            {
                "name": "POST /thermodynamic - Empty Data",
                "data": {},
                "expected_status": 200
            }
        ]
        
        for test_case in test_cases:
            result = self.make_request("POST", "/thermodynamic", test_case["data"])
            
            test_result = {
                "name": test_case["name"],
                "passed": False,
                "details": {}
            }
            
            if result["success"]:
                if result["status_code"] == test_case["expected_status"]:
                    data = result["data"]
                    
                    if "success" in data and data["success"]:
                        # Check for required fields
                        required_fields = ["listing_id", "breakdown"]
                        if all(field in data for field in required_fields):
                            breakdown = data["breakdown"]
                            
                            # Check breakdown structure
                            expected_breakdown_fields = [
                                "model_score", "entropy_measure", "system_temperature",
                                "utility_term", "entropy_term", "free_energy",
                                "selection_probability", "total_candidates", "cluster_count",
                                "selection_method"
                            ]
                            
                            if all(field in breakdown for field in expected_breakdown_fields):
                                # Validate numeric fields
                                numeric_fields = [
                                    "model_score", "entropy_measure", "system_temperature",
                                    "utility_term", "entropy_term", "free_energy",
                                    "selection_probability"
                                ]
                                
                                valid_numerics = True
                                for field in numeric_fields:
                                    if not isinstance(breakdown[field], (int, float)):
                                        valid_numerics = False
                                        break
                                
                                if valid_numerics:
                                    test_result["passed"] = True
                                    test_result["details"] = {
                                        "status_code": result["status_code"],
                                        "listing_id": data["listing_id"],
                                        "selection_method": breakdown["selection_method"],
                                        "selection_probability": breakdown["selection_probability"],
                                        "message": "Thermodynamic selection successful"
                                    }
                                else:
                                    test_result["details"] = {
                                        "status_code": result["status_code"],
                                        "error": "Invalid numeric values in breakdown",
                                        "breakdown": breakdown
                                    }
                            else:
                                missing_fields = [f for f in expected_breakdown_fields if f not in breakdown]
                                test_result["details"] = {
                                    "status_code": result["status_code"],
                                    "error": f"Missing breakdown fields: {missing_fields}",
                                    "breakdown": breakdown
                                }
                        else:
                            missing_fields = [f for f in required_fields if f not in data]
                            test_result["details"] = {
                                "status_code": result["status_code"],
                                "error": f"Missing required fields: {missing_fields}",
                                "response": data
                            }
                    else:
                        test_result["details"] = {
                            "status_code": result["status_code"],
                            "error": "Thermodynamic selection failed",
                            "response": data
                        }
                else:
                    test_result["details"] = {
                        "status_code": result["status_code"],
                        "error": f"Expected {test_case['expected_status']}, got {result['status_code']}",
                        "response": result["data"]
                    }
            else:
                test_result["details"] = {
                    "error": result["error"],
                    "message": "Failed to make request"
                }
            
            self.test_results.append(test_result)
            print(f"{'✅' if test_result['passed'] else '❌'} {test_result['name']}")
    
    def test_performance(self):
        """Test performance characteristics"""
        print("\n🔍 Testing Performance...")
        
        # Test concurrent requests
        def make_concurrent_request():
            return self.make_request("POST", "/predict", {"listing_ids": [1, 2, 3, 4, 5]})
        
        print("Testing concurrent requests...")
        start_time = time.time()
        
        threads = []
        results = []
        
        for i in range(10):
            thread = threading.Thread(target=lambda: results.append(make_concurrent_request()))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        duration = end_time - start_time
        
        successful_requests = sum(1 for r in results if r["success"] and r["status_code"] == 200)
        
        test_result = {
            "name": "Performance - Concurrent Requests",
            "passed": successful_requests >= 8,  # At least 80% success rate
            "details": {
                "duration": round(duration, 2),
                "successful_requests": successful_requests,
                "total_requests": 10,
                "success_rate": f"{(successful_requests/10)*100:.1f}%",
                "message": f"Handled {successful_requests}/10 concurrent requests in {duration:.2f}s"
            }
        }
        
        self.test_results.append(test_result)
        print(f"{'✅' if test_result['passed'] else '❌'} {test_result['name']}")
        
        # Test large payload
        print("Testing large payload...")
        large_payload = {"listing_ids": list(range(1, 1001))}  # 1000 IDs
        
        start_time = time.time()
        result = self.make_request("POST", "/predict", large_payload, timeout=30)
        end_time = time.time()
        duration = end_time - start_time
        
        test_result = {
            "name": "Performance - Large Payload",
            "passed": result["success"] and result["status_code"] == 200 and duration < 10,
            "details": {
                "duration": round(duration, 2),
                "status_code": result["status_code"],
                "success": result["success"],
                "payload_size": len(large_payload["listing_ids"]),
                "message": f"Processed {len(large_payload['listing_ids'])} IDs in {duration:.2f}s"
            }
        }
        
        if result["success"] and "data" in result and "predictions" in result["data"]:
            test_result["details"]["predictions_returned"] = len(result["data"]["predictions"])
        
        self.test_results.append(test_result)
        print(f"{'✅' if test_result['passed'] else '❌'} {test_result['name']}")
    
    def test_error_handling(self):
        """Test error handling scenarios"""
        print("\n🔍 Testing Error Handling...")
        
        # Test invalid JSON
        try:
            response = requests.post(f"{self.base_url}/predict", data="invalid json", 
                                   headers={"Content-Type": "application/json"})
            
            test_result = {
                "name": "Error Handling - Invalid JSON",
                "passed": response.status_code >= 400,  # Should return error status
                "details": {
                    "status_code": response.status_code,
                    "message": "Correctly handled invalid JSON"
                }
            }
        except Exception as e:
            test_result = {
                "name": "Error Handling - Invalid JSON",
                "passed": False,
                "details": {
                    "error": str(e),
                    "message": "Failed to test invalid JSON handling"
                }
            }
        
        self.test_results.append(test_result)
        print(f"{'✅' if test_result['passed'] else '❌'} {test_result['name']}")
        
        # Test nonexistent endpoint
        result = self.make_request("GET", "/nonexistent")
        
        test_result = {
            "name": "Error Handling - Nonexistent Endpoint",
            "passed": not result["success"] or result["status_code"] == 404,
            "details": {
                "status_code": result["status_code"],
                "success": result["success"],
                "message": "Correctly handled nonexistent endpoint"
            }
        }
        
        self.test_results.append(test_result)
        print(f"{'✅' if test_result['passed'] else '❌'} {test_result['name']}")
    
    def run_all_tests(self):
        """Run all test suites"""
        print("=" * 60)
        print("🧪 COMPREHENSIVE PYTHON SERVICES TESTING")
        print("=" * 60)
        
        # Check if service is already running
        health_check = self.make_request("GET", "/health", timeout=2)
        service_was_running = health_check["success"]
        
        if not service_was_running:
            if not self.start_service():
                print("❌ Failed to start service. Exiting.")
                return False
        else:
            print("✅ Service already running")
        
        try:
            # Run all test suites
            self.test_health_endpoint()
            self.test_predict_endpoint()
            self.test_train_endpoint()
            self.test_thermodynamic_endpoint()
            self.test_performance()
            self.test_error_handling()
            
        finally:
            if not service_was_running:
                self.stop_service()
        
        # Print summary
        self.print_summary()
        
        # Return overall success
        passed_tests = sum(1 for test in self.test_results if test["passed"])
        total_tests = len(self.test_results)
        
        return passed_tests == total_tests
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed_tests = sum(1 for test in self.test_results if test["passed"])
        total_tests = len(self.test_results)
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests < total_tests:
            print("\n❌ FAILED TESTS:")
            for test in self.test_results:
                if not test["passed"]:
                    print(f"  • {test['name']}")
                    if "error" in test["details"]:
                        print(f"    Error: {test['details']['error']}")
        
        print("\n" + "=" * 60)
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED!")
        else:
            print("⚠️  SOME TESTS FAILED - CHECK DETAILS ABOVE")
        print("=" * 60)

def main():
    """Main test runner"""
    tester = PythonServiceTester()
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        tester.stop_service()
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        tester.stop_service()
        sys.exit(1)

if __name__ == "__main__":
    main()
