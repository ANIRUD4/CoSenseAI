/**
 * companion-app/src/screens/MarketplaceScreen.js
 *
 * Browse shared models from the IntelShare AI marketplace.
 * Users can:
 *  - Browse all public models
 *  - Import a model from another user (bypasses the Learn phase entirely)
 *  - Export their own current model to share
 */

import React, { useState, useCallback } from 'react';
import {
    View, Text, StyleSheet, FlatList, TouchableOpacity,
    ActivityIndicator, RefreshControl, Modal, TextInput,
    Alert, ScrollView,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { listModels, exportModel, importModel } from '../services/api';

const COLORS = {
    bg: '#0A0F1E',
    card: '#111827',
    border: '#1F2937',
    primary: '#3B82F6',
    success: '#10B981',
    danger: '#EF4444',
    text: '#F9FAFB',
    muted: '#6B7280',
    purple: '#8B5CF6',
    yellow: '#FBBF24',
};

function formatDate(ts) {
    if (!ts) return '';
    return new Date(ts * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatSize(bytes) {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

export default function MarketplaceScreen() {
    const [models, setModels] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refresh, setRefresh] = useState(false);
    const [error, setError] = useState(null);
    const [importingId, setImportingId] = useState(null);

    // Export modal state
    const [showExport, setShowExport] = useState(false);
    const [exportName, setExportName] = useState('');
    const [exportDesc, setExportDesc] = useState('');
    const [exportAuthor, setExportAuthor] = useState('');
    const [exporting, setExporting] = useState(false);

    const loadModels = async (isRefresh = false) => {
        if (isRefresh) setRefresh(true);
        else setLoading(true);
        setError(null);
        try {
            const res = await listModels();
            setModels(res.data.models ?? []);
        } catch {
            setError('Could not reach the Raspberry Pi.\nCheck the IP in src/services/api.js.');
        } finally {
            setLoading(false);
            setRefresh(false);
        }
    };

    useFocusEffect(useCallback(() => { loadModels(); }, []));

    const handleImport = async (model) => {
        Alert.alert(
            `Import "${model.name}"?`,
            `By ${model.author}. This will add the model's learned labels to your Raspberry Pi. Your existing labels won't be removed.`,
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Import',
                    onPress: async () => {
                        setImportingId(model.id);
                        try {
                            await importModel(model.id);
                            Alert.alert('✓ Imported!', `"${model.name}" is now available on your Raspberry Pi.`);
                        } catch (e) {
                            Alert.alert('Import Failed', e.response?.data?.detail ?? 'An error occurred.');
                        } finally {
                            setImportingId(null);
                        }
                    },
                },
            ]
        );
    };

    const handleExport = async () => {
        if (!exportName.trim()) {
            Alert.alert('Name required', 'Please give your model a name.');
            return;
        }
        setExporting(true);
        try {
            await exportModel({
                name: exportName.trim(),
                description: exportDesc.trim(),
                author: exportAuthor.trim() || 'Anonymous',
            });
            setShowExport(false);
            setExportName(''); setExportDesc(''); setExportAuthor('');
            Alert.alert('✓ Published!', 'Your model is now visible in the marketplace.');
            loadModels();
        } catch (e) {
            Alert.alert('Export failed', e.response?.data?.detail ?? 'An error occurred.');
        } finally {
            setExporting(false);
        }
    };

    const renderModel = ({ item }) => (
        <View style={styles.card}>
            <View style={styles.cardHeader}>
                <Text style={styles.modelName} numberOfLines={1}>{item.name}</Text>
                <Text style={styles.modelSize}>{formatSize(item.file_size)}</Text>
            </View>
            {item.description ? (
                <Text style={styles.modelDesc} numberOfLines={2}>{item.description}</Text>
            ) : null}
            <View style={styles.cardFooter}>
                <View>
                    <Text style={styles.authorText}>👤 {item.author}</Text>
                    <Text style={styles.dateText}>{formatDate(item.created_at)}</Text>
                </View>
                <TouchableOpacity
                    style={[styles.importBtn, importingId === item.id && styles.importBtnDisabled]}
                    onPress={() => handleImport(item)}
                    disabled={importingId === item.id}
                >
                    {importingId === item.id ? (
                        <ActivityIndicator size="small" color="#fff" />
                    ) : (
                        <Text style={styles.importBtnText}>Import</Text>
                    )}
                </TouchableOpacity>
            </View>
        </View>
    );

    return (
        <View style={styles.container}>
            {/* Publish button */}
            <TouchableOpacity style={styles.publishBtn} onPress={() => setShowExport(true)}>
                <Text style={styles.publishText}>⬆ Publish my model</Text>
            </TouchableOpacity>

            {loading ? (
                <View style={styles.center}>
                    <ActivityIndicator size="large" color={COLORS.primary} />
                    <Text style={[styles.muted, { marginTop: 12 }]}>Loading marketplace…</Text>
                </View>
            ) : error ? (
                <View style={styles.center}>
                    <Text style={styles.errorText}>{error}</Text>
                    <TouchableOpacity onPress={() => loadModels()} style={styles.retryBtn}>
                        <Text style={styles.retryText}>Retry</Text>
                    </TouchableOpacity>
                </View>
            ) : models.length === 0 ? (
                <View style={styles.center}>
                    <Text style={styles.emptyIcon}>🛒</Text>
                    <Text style={styles.muted}>No models published yet.{'\n'}Be the first to share yours!</Text>
                </View>
            ) : (
                <FlatList
                    data={models}
                    keyExtractor={item => item.id}
                    renderItem={renderModel}
                    contentContainerStyle={styles.list}
                    refreshControl={
                        <RefreshControl
                            refreshing={refresh}
                            onRefresh={() => loadModels(true)}
                            tintColor={COLORS.primary}
                        />
                    }
                    ListHeaderComponent={
                        <Text style={styles.countText}>{models.length} model{models.length !== 1 ? 's' : ''} available</Text>
                    }
                />
            )}

            {/* ── Export modal ── */}
            <Modal visible={showExport} animationType="slide" transparent>
                <View style={styles.modalOverlay}>
                    <View style={styles.modalCard}>
                        <Text style={styles.modalTitle}>Publish your model</Text>
                        <Text style={styles.modalSubtitle}>
                            Share your trained labels so others can import them without going through Learn mode.
                        </Text>
                        <TextInput
                            style={styles.modalInput}
                            value={exportName}
                            onChangeText={setExportName}
                            placeholder="Model name (e.g. Empty Bottle Detector)"
                            placeholderTextColor={COLORS.muted}
                        />
                        <TextInput
                            style={[styles.modalInput, { height: 80 }]}
                            value={exportDesc}
                            onChangeText={setExportDesc}
                            placeholder="Description (optional)"
                            placeholderTextColor={COLORS.muted}
                            multiline
                        />
                        <TextInput
                            style={styles.modalInput}
                            value={exportAuthor}
                            onChangeText={setExportAuthor}
                            placeholder="Your name (optional)"
                            placeholderTextColor={COLORS.muted}
                        />
                        <View style={styles.modalButtons}>
                            <TouchableOpacity
                                onPress={() => { setShowExport(false); setExportName(''); setExportDesc(''); setExportAuthor(''); }}
                                style={styles.cancelBtn}
                            >
                                <Text style={styles.cancelText}>Cancel</Text>
                            </TouchableOpacity>
                            <TouchableOpacity
                                onPress={handleExport}
                                style={[styles.submitBtn, exporting && { opacity: 0.6 }]}
                                disabled={exporting}
                            >
                                {exporting
                                    ? <ActivityIndicator size="small" color="#fff" />
                                    : <Text style={styles.submitText}>Publish</Text>}
                            </TouchableOpacity>
                        </View>
                    </View>
                </View>
            </Modal>
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: COLORS.bg },
    center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
    list: { paddingHorizontal: 16, paddingBottom: 32 },
    publishBtn: { margin: 16, backgroundColor: COLORS.purple, borderRadius: 12, padding: 14, alignItems: 'center' },
    publishText: { color: '#fff', fontWeight: '800', fontSize: 15, letterSpacing: 0.5 },
    countText: { fontSize: 11, color: COLORS.muted, marginVertical: 8, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.8 },
    card: { backgroundColor: COLORS.card, borderRadius: 16, borderWidth: 1, borderColor: COLORS.border, marginBottom: 12, padding: 16 },
    cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 },
    modelName: { fontSize: 16, fontWeight: '800', color: COLORS.text, flex: 1, marginRight: 8 },
    modelSize: { fontSize: 11, color: COLORS.muted, fontWeight: '600', marginTop: 2 },
    modelDesc: { fontSize: 13, color: COLORS.muted, marginBottom: 12, lineHeight: 18 },
    cardFooter: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
    authorText: { fontSize: 12, color: COLORS.muted, fontWeight: '600' },
    dateText: { fontSize: 11, color: COLORS.muted, marginTop: 2 },
    importBtn: { backgroundColor: COLORS.primary, borderRadius: 10, paddingHorizontal: 18, paddingVertical: 8, minWidth: 80, alignItems: 'center' },
    importBtnDisabled: { opacity: 0.5 },
    importBtnText: { color: '#fff', fontWeight: '700', fontSize: 13 },
    muted: { color: COLORS.muted, textAlign: 'center', lineHeight: 22, fontSize: 14 },
    emptyIcon: { fontSize: 48, marginBottom: 12 },
    errorText: { color: '#F87171', textAlign: 'center', lineHeight: 22, marginBottom: 16, fontSize: 14 },
    retryBtn: { backgroundColor: COLORS.primary, paddingHorizontal: 24, paddingVertical: 10, borderRadius: 10 },
    retryText: { color: '#fff', fontWeight: '700', fontSize: 14 },
    // Modal
    modalOverlay: { flex: 1, backgroundColor: '#00000090', justifyContent: 'flex-end' },
    modalCard: { backgroundColor: COLORS.card, borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 24, paddingBottom: 40 },
    modalTitle: { fontSize: 20, fontWeight: '900', color: COLORS.text, marginBottom: 6 },
    modalSubtitle: { fontSize: 13, color: COLORS.muted, marginBottom: 20, lineHeight: 18 },
    modalInput: { backgroundColor: '#1F2937', borderRadius: 12, padding: 14, color: COLORS.text, fontSize: 14, marginBottom: 12, textAlignVertical: 'top' },
    modalButtons: { flexDirection: 'row', gap: 10, marginTop: 4 },
    cancelBtn: { flex: 1, borderWidth: 1, borderColor: COLORS.border, borderRadius: 12, padding: 14, alignItems: 'center' },
    cancelText: { color: COLORS.muted, fontWeight: '700' },
    submitBtn: { flex: 2, backgroundColor: COLORS.purple, borderRadius: 12, padding: 14, alignItems: 'center' },
    submitText: { color: '#fff', fontWeight: '800', fontSize: 15 },
});
